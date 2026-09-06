import tempfile
import os

from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ingestion.extractor import UnsupportedFileType
from ingestion.pipeline import IngestionPipeline
from llm.client import LLMError, OpenRouterClient
from llm.prompts import build_synthesis_prompt
from llm.schemas import FinalAnswer
from retrieval.evidence import EvidenceBuilder
from retrieval.executor import SQLExecutor
from retrieval.graph import GraphBuilder
from retrieval.planner import QueryPlanner

from .models import Chunk, Document, QueryAudit
from .serializers import (
    AskRequestSerializer,
    AskResponseSerializer,
    ChunkSerializer,
    DocumentSerializer,
)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer


class ChunkViewSet(viewsets.ModelViewSet):
    queryset = Chunk.objects.all()
    serializer_class = ChunkSerializer


class DocumentIngestView(APIView):
    """Upload a file, run it through the ingestion pipeline, and store it as a Document."""

    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        _, ext = os.path.splitext(upload.name)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            document = IngestionPipeline().ingest_file(tmp_path, title=upload.name)
        except UnsupportedFileType as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            os.remove(tmp_path)

        return Response(
            DocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class AskView(APIView):
    """Vectorless RAG entrypoint: plan SQL -> execute -> synthesize -> build graph."""

    def post(self, request):
        request_serializer = AskRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        question = request_serializer.validated_data['question']

        client = OpenRouterClient()
        planner = QueryPlanner(client)
        executor = SQLExecutor()
        evidence_builder = EvidenceBuilder()
        graph_builder = GraphBuilder()

        try:
            plan = planner.plan(question)
        except LLMError as exc:
            return Response({'detail': str(exc)}, status=502)

        results = executor.execute_plan(plan)

        QueryAudit.objects.bulk_create(
            QueryAudit(
                question=question,
                sql=query.sql,
                rationale=query.rationale,
                status='failed' if result.error else 'executed',
                row_count=result.row_count,
                error=result.error or '',
            )
            for query, result in zip(plan.queries, results)
        )

        evidence = evidence_builder.build(results)

        try:
            synthesis_raw = client.chat_json(
                build_synthesis_prompt(question, evidence_builder.render(evidence))
            )
            answer = FinalAnswer.model_validate(synthesis_raw)
        except LLMError as exc:
            return Response({'detail': str(exc)}, status=502)

        graph = graph_builder.build(question, evidence, answer)

        response_serializer = AskResponseSerializer(
            {
                'answer': answer.answer,
                'citations': answer.citations,
                'evidence': [item.model_dump() for item in evidence],
                'graph': graph.model_dump(),
                'queries': [result.model_dump() for result in results],
            }
        )
        return Response(response_serializer.data)
