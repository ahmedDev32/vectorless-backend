"""Dispatches a file to the right extractor in extractors.py based on its extension."""

import os

from . import extractors

_BY_EXTENSION = {
    '.txt': extractors.extract_txt,
    '.md': extractors.extract_txt,
    '.csv': extractors.extract_csv,
    '.pdf': extractors.extract_pdf,
    '.docx': extractors.extract_docx,
    '.pptx': extractors.extract_pptx,
}


class UnsupportedFileType(ValueError):
    pass


class Extractor:
    def supports(self, path: str) -> bool:
        _, ext = os.path.splitext(path)
        return ext.lower() in _BY_EXTENSION

    def extract(self, path: str) -> str:
        _, ext = os.path.splitext(path)
        func = _BY_EXTENSION.get(ext.lower())
        if func is None:
            raise UnsupportedFileType(f'No extractor registered for "{ext}".')
        return func(path)
