import re
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import connection, connections, transaction

from llm.schemas import QueryResult, SQLQuery, SQLQueryPlan

_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|execute|call|copy|merge|vacuum|comment)\b',
    re.IGNORECASE,
)


class RejectedQuery(ValueError):
    pass


def validate_select_only(sql: str) -> None:
    """Reject anything that isn't a single, read-only SELECT statement."""
    stripped = sql.strip().rstrip(';').strip()
    if not stripped:
        raise RejectedQuery('Empty query.')
    if ';' in stripped:
        raise RejectedQuery('Multiple statements are not allowed.')
    if not re.match(r'^\s*(select|with)\b', stripped, re.IGNORECASE):
        raise RejectedQuery('Only SELECT statements are allowed.')
    if _FORBIDDEN_KEYWORDS.search(stripped):
        raise RejectedQuery('Query contains a forbidden keyword.')


class SQLExecutor:
    """Executes LLM-proposed SQL queries against the database in a read-only, capped manner."""

    def __init__(self, max_rows: int | None = None, timeout_ms: int | None = None):
        self.max_rows = max_rows or settings.SQL_QUERY_MAX_ROWS
        self.timeout_ms = timeout_ms or settings.SQL_QUERY_TIMEOUT_MS

    def execute_one(self, query: SQLQuery) -> QueryResult:
        try:
            validate_select_only(query.sql)
        except RejectedQuery as exc:
            return QueryResult(query=query, error=str(exc))

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SET LOCAL statement_timeout = %s', [self.timeout_ms])
                    cursor.execute('SET TRANSACTION READ ONLY')
                    cursor.execute(query.sql)
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchmany(self.max_rows)
                # Always roll back: these queries must never persist side effects,
                # even if validate_select_only somehow let something slip through.
                transaction.set_rollback(True)
        except Exception as exc:  # database driver errors vary by backend
            return QueryResult(query=query, error=str(exc))

        dict_rows = [dict(zip(columns, row)) for row in rows]
        return QueryResult(query=query, columns=columns, rows=dict_rows, row_count=len(dict_rows))

    def _execute_one_in_worker_thread(self, query: SQLQuery) -> QueryResult:
        # Each thread gets its own lazily-opened Django DB connection; it must be
        # closed explicitly here since Django's normal per-request cleanup only
        # runs on the main thread.
        try:
            return self.execute_one(query)
        finally:
            connections.close_all()

    def execute_plan(self, plan: SQLQueryPlan) -> list[QueryResult]:
        if len(plan.queries) <= 1:
            return [self.execute_one(query) for query in plan.queries]

        # Independent read-only queries don't depend on each other, so run them
        # concurrently instead of paying their latency serially.
        with ThreadPoolExecutor(max_workers=min(len(plan.queries), 8)) as pool:
            return list(pool.map(self._execute_one_in_worker_thread, plan.queries))
