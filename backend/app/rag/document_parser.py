"""PDF and DOCX document text extraction — Phase 04C.

Uses pypdf for PDF and python-docx for DOCX.  No macros, scripts, or
embedded objects are executed.
"""

from __future__ import annotations

import io
from pathlib import Path


class DocumentParseError(Exception):
    """Controlled, user-safe parse error — never exposes internal paths or stacks."""


def parse_pdf(data: bytes, max_size_mb: int = 10) -> str:
    """Extract text from a PDF byte stream.

    Raises ``DocumentParseError`` for empty, encrypted, or unreadable PDFs.
    """
    if len(data) == 0:
        raise DocumentParseError("上传的文件为空")
    if len(data) > max_size_mb * 1024 * 1024:
        raise DocumentParseError(f"文件超过最大限制 {max_size_mb}MB")

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))

        if reader.is_encrypted:
            raise DocumentParseError("PDF 文件已加密，无法解析")

        text_parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n".join(text_parts).strip()
        if not full_text:
            raise DocumentParseError("PDF 文件中未提取到文本内容")

        return full_text
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("PDF 文件损坏或格式不支持，无法解析") from exc


def parse_docx(data: bytes, max_size_mb: int = 10) -> str:
    """Extract text from a DOCX byte stream.

    Raises ``DocumentParseError`` for empty or corrupted DOCX files.
    """
    if len(data) == 0:
        raise DocumentParseError("上传的文件为空")
    if len(data) > max_size_mb * 1024 * 1024:
        raise DocumentParseError(f"文件超过最大限制 {max_size_mb}MB")

    try:
        from docx import Document
        doc = Document(io.BytesIO(data))

        text_parts: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        full_text = "\n".join(text_parts).strip()
        if not full_text:
            raise DocumentParseError("DOCX 文件中未提取到文本内容")

        return full_text
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("DOCX 文件损坏或格式不支持，无法解析") from exc


def parse_upload(data: bytes, filename: str, max_size_mb: int = 10) -> str:
    """Dispatch to the appropriate parser based on file extension.

    Only ``.pdf`` and ``.docx`` are accepted.
    """
    suffix = Path(filename).suffix.lower()
    name_only = Path(filename).name  # strip any directory components

    if ".." in name_only or "/" in name_only or "\\" in name_only:
        raise DocumentParseError("文件名包含非法字符")

    if suffix == ".pdf":
        return parse_pdf(data, max_size_mb)
    elif suffix in (".docx", ".doc"):
        return parse_docx(data, max_size_mb)
    else:
        raise DocumentParseError(f"不支持的文件格式: {suffix}。仅支持 PDF 和 DOCX 文件。")
