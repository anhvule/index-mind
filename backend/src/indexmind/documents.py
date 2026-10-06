"""Reading supported files from disk into plain-text sections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".markdown", ".txt"})

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class Section:
    """A contiguous piece of a document with enough context to cite it."""

    text: str
    page: int | None = None
    heading: str | None = None


def is_supported(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and not path.name.startswith(".")
    )


def read_sections(path: Path) -> list[Section]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".md", ".markdown"}:
        return split_markdown(text)
    return [Section(text=text)] if text.strip() else []


def _read_pdf(path: Path) -> list[Section]:
    # pdfium keeps words intact where simpler extractors split them at every glyph
    # run, which badly breaks text with stacked diacritics such as Vietnamese.
    document = pdfium.PdfDocument(path)
    try:
        sections = []
        for number, page in enumerate(document, start=1):
            text = page.get_textpage().get_text_range().replace("\r\n", "\n")
            if text.strip():
                sections.append(Section(text=text, page=number))
        return sections
    finally:
        document.close()


def split_markdown(text: str) -> list[Section]:
    """Split Markdown at headings, labelling each part with its heading trail ("A / B")."""
    trail: list[tuple[int, str]] = []
    sections: list[Section] = []
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            heading = " / ".join(title for _, title in trail) or None
            sections.append(Section(text=body, heading=heading))
        buffer.clear()

    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _MD_HEADING.match(line)
        if match is None:
            buffer.append(line)
            continue
        flush()
        level, title = len(match.group(1)), match.group(2)
        trail = [(lvl, t) for lvl, t in trail if lvl < level]
        trail.append((level, title))
    flush()
    return sections
