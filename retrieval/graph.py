from llm.schemas import Evidence, EvidenceGraph, FinalAnswer, GraphEdge, GraphNode


class GraphBuilder:
    """Assembles the evidence graph linking the question, evidence rows, and cited answer."""

    def build(self, question: str, evidence: list[Evidence], answer: FinalAnswer) -> EvidenceGraph:
        nodes = [GraphNode(id='question', label=question, type='question')]
        nodes.append(GraphNode(id='answer', label=answer.answer, type='answer'))
        edges = []

        evidence_by_id = {item.id: item for item in evidence}
        for item in evidence:
            nodes.append(GraphNode(id=item.id, label=item.text, type='evidence'))
            edges.append(GraphEdge(source='question', target=item.id, relation='retrieved'))

        for citation_id in answer.citations:
            if citation_id in evidence_by_id:
                edges.append(GraphEdge(source=citation_id, target='answer', relation='supports'))

        return EvidenceGraph(nodes=nodes, edges=edges)
