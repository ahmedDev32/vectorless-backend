from llm.schemas import Evidence, QueryResult

# When a row includes the chunk's content column, that IS the evidence - use it
# verbatim rather than a flattened "content=..., document_id=1, order=0" dump,
# so the answering LLM is grounded in real document text, not a metadata blob.
_PRIMARY_TEXT_COLUMNS = ('content',)


class EvidenceBuilder:
    """Flattens raw query results into citable evidence rows."""

    def build(self, results: list[QueryResult]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for result in results:
            if result.error:
                continue
            for row in result.rows:
                evidence.append(
                    Evidence(
                        id=f'e{len(evidence)}',
                        text=self._row_text(row),
                        source_sql=result.query.sql,
                        row=row,
                    )
                )
        return evidence

    def _row_text(self, row: dict) -> str:
        for column in _PRIMARY_TEXT_COLUMNS:
            value = row.get(column)
            if value:
                return str(value)
        return ', '.join(f'{k}={v}' for k, v in row.items())

    def render(self, evidence: list[Evidence]) -> str:
        return '\n'.join(f'[{item.id}] {item.text}' for item in evidence) or '(no evidence found)'
