"""Split a Markdown document into retrieval-sized chunks.

1. Split on `## ` headings (one topic each).
2. Split a section longer than `max_chars` on paragraph, then sentence boundaries,
   carrying ~`overlap` characters of context into the next piece.
3. Every chunk starts with its heading, so a chunk still makes sense on its own.
"""

import re
from dataclasses import dataclass

_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    chunks: list[str]


def parse_markdown(
    text: str, fallback_title: str, max_chars: int = 800, overlap: int = 100
) -> ParsedDocument:
    title = fallback_title
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        if line.startswith("# ") and title == fallback_title:
            title = line[2:].strip()
        elif line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)

    chunks: list[str] = []
    for heading, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        prefix = f"{title} — {heading}\n" if heading else f"{title}\n"
        for piece in _split(body, max_chars - len(prefix), overlap):
            chunks.append(prefix + piece)
    return ParsedDocument(title=title, chunks=chunks)


def _split(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    # Units = paragraphs, and sentences of any paragraph that is itself too long.
    units: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            units.append(paragraph)
        else:
            units.extend(
                part
                for sentence in _SENTENCE_END.split(paragraph)
                for part in _hard_split(sentence, max_chars)
            )

    pieces: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
            tail = _tail(current, overlap)
            current = (
                f"{tail}\n\n{unit}" if tail and len(tail) + len(unit) + 2 <= max_chars else unit
            )
        else:
            current = unit
    if current:
        pieces.append(current)
    return pieces


def _hard_split(sentence: str, max_chars: int) -> list[str]:
    """A single sentence longer than max_chars (rare) is cut on word boundaries."""
    if len(sentence) <= max_chars:
        return [sentence]
    parts: list[str] = []
    current = ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > max_chars:
            parts.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        parts.append(current)
    return parts


def _tail(text: str, overlap: int) -> str:
    """The last ~overlap characters, starting at a sentence or word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return ""
    tail = text[-overlap:]
    sentences = _SENTENCE_END.split(tail)
    if len(sentences) > 1:
        return " ".join(sentences[1:]).strip()
    return tail.split(" ", 1)[-1].strip()
