"""Chinese-friendly text chunking — sentence-boundary, character-budget."""

from __future__ import annotations

import re

# Sentence boundary delimiters (Chinese + ASCII)
_SENTENCE_RE = re.compile(r"(?<=[。！？；.!?;])\s*")

# Paragraph separator
_PARAGRAPH_RE = re.compile(r"\n\s*\n")


def chunk_text(
    text: str,
    max_chars: int = 500,
    overlap_chars: int = 50,
) -> list[str]:
    """Split *text* into overlapping chunks at natural boundaries.

    1. Split on paragraph breaks (``\\n\\n+``) first.
    2. Within each paragraph, split on sentence delimiters: ``。！？；.!?;``
    3. Greedy-merge complete sentences into chunks ≤ *max_chars*.
    4. Each chunk (except the first) starts with the last 1–2 complete
       trailing sentences from the previous chunk whose length ≤
       *overlap_chars*.
    5. A single sentence that exceeds *max_chars* is hard-cut at the
       *max_chars* boundary (no overlap between the resulting segments).

    Parameters
    ----------
    text:
        Raw input text (Chinese, English, or mixed).
    max_chars:
        Maximum character count per chunk (soft limit, exceeded only by
        hard-cut long sentences).
    overlap_chars:
        Approximate character count of overlap text carried forward from
        the previous chunk.

    Returns
    -------
    list[str]
        Chunks with leading/trailing whitespace stripped.  Never
        contains empty strings.  Returns an empty list for empty or
        whitespace-only input.
    """
    # ── Guard: empty / whitespace-only ──────────────────────────────
    stripped = text.strip()
    if not stripped:
        return []

    # ── Paragraph split ─────────────────────────────────────────────
    paragraphs = _PARAGRAPH_RE.split(stripped)

    all_chunks: list[str] = []
    last_sentences: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        sentences = _split_sentences(para)
        if not sentences:
            continue

        # Merge overlap from previous chunk if present
        if last_sentences:
            sentences = last_sentences + sentences
            last_sentences = []

        chunks, carry = _merge_sentences(sentences, max_chars, overlap_chars)
        all_chunks.extend(chunks)
        last_sentences = carry

    # Flush remaining carry sentences — carry is for the NEXT batch,
    # so if there are no more paragraphs, carry is already consumed.
    # Only flush a trailing chunk when the carry would not duplicate
    # the last chunk's content.
    if last_sentences:
        carry_text = "".join(last_sentences).strip()
        if carry_text and carry_text not in all_chunks:
            all_chunks.append(carry_text)

    # ── Strip each chunk ────────────────────────────────────────────
    result = [c.strip() for c in all_chunks if c.strip()]
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_sentences(paragraph: str) -> list[str]:
    """Split *paragraph* into sentences on Chinese/ASCII delimiters."""
    parts = _SENTENCE_RE.split(paragraph)
    # _SENTENCE_RE with lookbehind keeps the delimiter with the preceding
    # sentence.  Filter out empty/whitespace strings.
    return [p for p in parts if p.strip()]


def _merge_sentences(
    sentences: list[str],
    max_chars: int,
    overlap_chars: int,
) -> tuple[list[str], list[str]]:
    """Greedy-merge *sentences* into <= *max_chars* chunks.

    Returns ``(chunks, carry_sentences)`` where *carry_sentences* are
    the trailing sentences to prepend to the next batch.
    """
    chunks: list[str] = []

    i = 0
    while i < len(sentences):
        sent = sentences[i]

        # ── Single long sentence: hard cut ──────────────────────────
        if len(sent) > max_chars:
            # Flush current in-progress chunk
            # (handled by the else branch below)

            # Hard-cut this sentence
            for start in range(0, len(sent), max_chars):
                piece = sent[start : start + max_chars].strip()
                if piece:
                    chunks.append(piece)
            i += 1
            continue

        # ── Greedy merge ────────────────────────────────────────────
        current: list[str] = []
        while i < len(sentences) and len("".join(current)) + len(sentences[i]) <= max_chars:
            current.append(sentences[i])
            i += 1

        if current:
            chunk_text_val = "".join(current).strip()
            if chunk_text_val:
                chunks.append(chunk_text_val)

    # ── Compute overlap carry for the next call ─────────────────────
    carry: list[str] = []
    if chunks and overlap_chars > 0:
        # Walk backward through the last chunk's sentences to find overlap
        last_chunk = chunks[-1]
        # Re-split to get sentences within the chunk
        chunk_sentences = _split_sentences(last_chunk)
        # Take the last N sentences whose combined length ≤ overlap_chars
        carry_chars = 0
        for s in reversed(chunk_sentences):
            if carry_chars + len(s) > overlap_chars:
                break
            carry.insert(0, s)
            carry_chars += len(s)

    return chunks, carry
