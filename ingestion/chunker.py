"""Splits cleaned text into overlapping chunks suitable for row-level storage."""


class TextChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 150):
        if overlap >= chunk_size:
            raise ValueError('overlap must be smaller than chunk_size')
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        chunks = []
        start = 0
        step = self.chunk_size - self.overlap
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end].strip())
            start += step
        return [c for c in chunks if c]
