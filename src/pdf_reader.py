"""
pdf_reader.py  –  PDF to Audiobook · PDF Text Extraction
Wraps pypdf with improved error handling and page-range support.
"""

import re
from pathlib import Path

try:
    import pypdf
    PYPDF_OK = True
except ImportError:
    PYPDF_OK = False


class PDFReadError(Exception):
    """Raised when a PDF cannot be read or yields no text."""


def extract_text(path: str | Path,
                 start_page: int = 0,
                 end_page: int | None = None) -> str:
    """
    Extract text from *path*.

    Parameters
    ----------
    path       : Path to the PDF file.
    start_page : 0-based index of the first page to extract (default 0).
    end_page   : 0-based index of the last page (inclusive).
                 None means extract all pages from start_page onward.

    Returns
    -------
    A single string with pages separated by double newlines.

    Raises
    ------
    PDFReadError if the file is missing, unreadable, or yields no text.
    """
    if not PYPDF_OK:
        raise PDFReadError(
            "pypdf is not installed.\n"
            "Run:  pip install pypdf"
        )

    path = Path(path)
    if not path.is_file():
        raise PDFReadError(f"File not found: {path}")

    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as exc:
        raise PDFReadError(f"Could not open PDF: {exc}") from exc

    total = len(reader.pages)
    if total == 0:
        raise PDFReadError("The PDF has no pages.")

    end = min(end_page + 1, total) if end_page is not None else total
    end = max(end, start_page + 1)

    parts: list[str] = []
    for i in range(start_page, end):
        try:
            text = reader.pages[i].extract_text() or ""
            if text.strip():
                parts.append(_clean(text))
        except Exception:
            pass  # skip unreadable pages rather than crashing

    if not parts:
        raise PDFReadError(
            "Could not extract any text from this PDF.\n"
            "It may be a scanned / image-only PDF.\n"
            "OCR support is not included in this version."
        )

    return "\n\n".join(parts)


def page_count(path: str | Path) -> int:
    """Return the number of pages, or 0 on failure."""
    try:
        return len(pypdf.PdfReader(str(path)).pages)
    except Exception:
        return 0


def _clean(text: str) -> str:
    """Light cleanup: remove excessive whitespace / garbage characters."""
    # collapse runs of whitespace (but keep newlines)
    text = re.sub(r"[^\S\n]+", " ", text)
    # remove lines that are only whitespace
    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    return "\n".join(lines)
