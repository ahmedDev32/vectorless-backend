"""Orchestrates extract -> clean -> chunk -> persist into Document/Chunk rows."""

import os

from knowledge.models import Chunk, Document

from .chunker import TextChunker
from .cleaner import TextCleaner
from .extractor import Extractor


class IngestionPipeline:
    def __init__(
        self,
        extractor: Extractor | None = None,
        cleaner: TextCleaner | None = None,
        chunker: TextChunker | None = None,
    ):
        self.extractor = extractor or Extractor()
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or TextChunker()

    def ingest_file(self, path: str, title: str | None = None) -> Document:
        raw_text = self.extractor.extract(path)
        cleaned_text = self.cleaner.clean(raw_text)
        chunks = self.chunker.chunk(cleaned_text)

        document = Document.objects.create(
            title=title or os.path.basename(path),
            source=path,
        )
        Chunk.objects.bulk_create(
            [
                Chunk(document=document, content=chunk, order=i)
                for i, chunk in enumerate(chunks)
            ]
        )
        return document
