"""Normalizes raw extracted text before chunking."""

import re

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
_MULTI_BLANK_LINES = re.compile(r'\n{3,}')
_TRAILING_SPACES = re.compile(r'[ \t]+\n')


class TextCleaner:
    def clean(self, text: str) -> str:
        text = _CONTROL_CHARS.sub('', text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = _TRAILING_SPACES.sub('\n', text)
        text = _MULTI_BLANK_LINES.sub('\n\n', text)
        return text.strip()
