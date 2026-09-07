from django.db import models


class Document(models.Model):
    title = models.CharField(max_length=255)
    source = models.CharField(max_length=1024, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.document_id}:{self.order}'


class QueryAudit(models.Model):
    """Audit trail for every LLM-generated SQL query that gets executed."""

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('executed', 'Executed'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ]

    question = models.TextField()
    sql = models.TextField()
    rationale = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='planned')
    row_count = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.status}] {self.sql[:60]}'
