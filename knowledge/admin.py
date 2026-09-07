from django.contrib import admin

from .models import Chunk, Document, QueryAudit


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'source', 'created_at')
    search_fields = ('title', 'source')


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'order')
    list_filter = ('document',)


@admin.register(QueryAudit)
class QueryAuditAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'row_count', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('question', 'sql', 'rationale', 'status', 'row_count', 'error', 'created_at')
