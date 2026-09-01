"""Read plain text out of a resume or job description file, regardless of
whether it's .txt, .pdf, or .docx - so extract_and_parse.py always sees the
same plain-text input no matter what format the user provided."""

from pathlib import Path

import pdfplumber
from docx import Document

SUPPORTED_EXTENSIONS = (".txt", ".pdf", ".docx")


def read_text(path):
    """Return the plain text content of a .txt, .pdf, or .docx file."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    if suffix == ".docx":
        return "\n".join(p.text for p in Document(path).paragraphs)

    raise ValueError(f"Unsupported file type: {suffix} (expected one of {SUPPORTED_EXTENSIONS})")
