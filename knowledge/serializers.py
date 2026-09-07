from rest_framework import serializers

from .models import Chunk, Document, QueryAudit


class ChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chunk
        fields = ['id', 'document', 'content', 'order', 'metadata']


class DocumentSerializer(serializers.ModelSerializer):
    chunks = ChunkSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ['id', 'title', 'source', 'created_at', 'updated_at', 'chunks']


class QueryAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryAudit
        fields = ['id', 'question', 'sql', 'rationale', 'status', 'row_count', 'error', 'created_at']


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(allow_blank=False)


class AskResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    citations = serializers.ListField(child=serializers.CharField())
    evidence = serializers.ListField(child=serializers.DictField())
    graph = serializers.DictField()
    queries = serializers.ListField(child=serializers.DictField())
