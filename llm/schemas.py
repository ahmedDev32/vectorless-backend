from typing import Any, Optional

from pydantic import BaseModel, Field


class SQLQuery(BaseModel):
    """A single read-only SQL query proposed by the LLM."""

    sql: str = Field(description='A single read-only SELECT statement.')
    rationale: str = Field(default='', description='Why this query helps answer the question.')


class SQLQueryPlan(BaseModel):
    """The set of SQL queries the LLM wants executed to answer a question."""

    queries: list[SQLQuery] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Raw result of executing one SQLQuery."""

    query: SQLQuery
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None


class Evidence(BaseModel):
    """A normalized fact extracted from a QueryResult, citable in the final answer."""

    id: str
    text: str
    source_sql: str
    row: dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class EvidenceGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class FinalAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
