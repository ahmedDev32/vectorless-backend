import json
import re

from django.apps import apps

from llm.client import OpenRouterClient
from llm.prompts import build_correction_prompt, build_planner_prompt
from llm.schemas import SQLQuery, SQLQueryPlan

# Column names alone don't tell the LLM what actually lives in them (e.g. "title"
# looks like free text but is really just a filename). Without this it guesses
# wrong tables/columns for content search, so spell it out per table.
_TABLE_NOTES = {
    'knowledge_document': (
        'One row per ingested file. "title" is usually just the original filename '
        '(e.g. "novadesk_overview.pdf"), NOT the document body - do not search it '
        'for company names, topics, or any free-text content. created_at/updated_at '
        'describe when this row was created/modified in the database, not a fact '
        'from inside the document.'
    ),
    'knowledge_chunk': (
        'The actual extracted document text lives here, in "content", split into '
        'ordered pieces per document (joined via document_id -> knowledge_document.id). '
        'Any question about what a document says, mentions, or is about must search '
        'AND select "content" here, not knowledge_document. A GIN full-text-search '
        "index exists on to_tsvector('english', content) for ranked/multi-keyword search."
    ),
}

_CONTENT_COLUMN = 'content'

_MAX_CORRECTION_ROUNDS = 1


def describe_schema() -> str:
    """Introspect Django models into a schema description annotated with column semantics."""
    lines = []
    for model in apps.get_app_config('knowledge').get_models():
        table = model._meta.db_table
        columns = ', '.join(field.column for field in model._meta.fields)
        lines.append(f'{table}({columns})')
        note = _TABLE_NOTES.get(table)
        if note:
            lines.append(f'  -- {note}')
    return '\n'.join(lines)


def _select_list(sql: str) -> str:
    match = re.search(r'select\s+(.*?)\s+from\s', sql, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ''


def _where_clause(sql: str) -> str:
    match = re.search(
        r'\bwhere\b(.*?)(\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)', sql, re.IGNORECASE | re.DOTALL
    )
    return match.group(1) if match else ''


def flag_metadata_confusion(query: SQLQuery) -> str | None:
    """Structural check: filtering on content but not returning it discards the evidence.

    This is deliberately generic - it looks at column usage in the SQL, not at the
    question text or any specific entity/document name, so it applies to arbitrary
    questions and documents.
    """
    select_list = _select_list(query.sql)
    where_clause = _where_clause(query.sql)

    filters_on_content = bool(re.search(rf'\b{_CONTENT_COLUMN}\b', where_clause, re.IGNORECASE))
    if not filters_on_content:
        return None

    selects_everything = '*' in select_list
    selects_content = selects_everything or bool(
        re.search(rf'\b{_CONTENT_COLUMN}\b', select_list, re.IGNORECASE)
    )
    if selects_content:
        return None

    return (
        f'This query filters on the "{_CONTENT_COLUMN}" column but does not include it in the '
        f'SELECT list, so the matching text itself will never be returned - only metadata '
        f'columns will. Add "{_CONTENT_COLUMN}" to the SELECT list.'
    )


class QueryPlanner:
    """Asks the LLM to turn a natural-language question into read-only SQL queries."""

    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()

    def plan(self, question: str) -> SQLQueryPlan:
        messages = build_planner_prompt(question, describe_schema())
        raw = self.client.chat_json(messages)
        plan = SQLQueryPlan.model_validate(raw)

        for _ in range(_MAX_CORRECTION_ROUNDS):
            issues = [flag_metadata_confusion(query) for query in plan.queries]
            issues = [issue for issue in issues if issue]
            if not issues:
                break
            correction_content = build_correction_prompt(
                json.dumps(plan.model_dump()), issues
            )
            messages = messages + [
                {'role': 'assistant', 'content': json.dumps(raw)},
                {'role': 'user', 'content': correction_content},
            ]
            raw = self.client.chat_json(messages)
            plan = SQLQueryPlan.model_validate(raw)

        return plan
