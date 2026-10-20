"""Text eines Abschnitts in Bausteine zerlegen: Überschriften, Absätze und Listen.

PDF, LaTeX und Word bauen alle auf diesen Bausteinen auf, damit sie den Text gleich verstehen.

Schreibweise im Textfeld:
- "# ", "## ", "### " am Zeilenanfang: Überschrift Ebene 1 bis 3 (Alt+1 bis Alt+3).
- "- ", "* " oder "• " am Zeilenanfang: Aufzählung mit Punkten.
- "1. " oder "1) " am Zeilenanfang: nummerierte Liste.
- Je zwei Leerzeichen (oder ein Tab) davor: eine Ebene tiefer in der Liste.
- Eine leere Zeile beendet einen Absatz oder eine Liste.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from konzeptheft.core.concept import heading_level, strip_heading

MAX_LIST_DEPTH = 4                     # LaTeX erlaubt vier Ebenen
_ITEM = re.compile(r"^([ \t]*)([-*•]|\d+[.)])[ \t]+(.*)$")


@dataclass
class Heading:
    level: int                         # 1 bis 3, wie im Textfeld
    text: str


@dataclass
class Paragraph:
    lines: list[str]


@dataclass
class ListItem:
    text: str
    sub: "ListBlock | None" = None


@dataclass
class ListBlock:
    ordered: bool
    items: list[ListItem] = field(default_factory=list)


Block = Heading | Paragraph | ListBlock


def _indent(spaces: str) -> int:
    width = sum(4 if c == "\t" else 1 for c in spaces)
    return min(width // 2, MAX_LIST_DEPTH - 1)


def parse(text: str) -> list[Block]:
    blocks: list[Block] = []
    paragraph: list[str] = []
    stack: list[tuple[int, ListBlock]] = []          # (Ebene, Liste), außen zuerst

    def end_paragraph() -> None:
        if paragraph:
            blocks.append(Paragraph(list(paragraph)))
            paragraph.clear()

    def end_list() -> None:
        stack.clear()

    for line in text.splitlines():
        item = _ITEM.match(line)
        if item and not heading_level(line):
            end_paragraph()
            depth, ordered = _indent(item.group(1)), item.group(2)[0].isdigit()
            while stack and stack[-1][0] > depth:
                stack.pop()
            if stack and stack[-1][0] == depth and stack[-1][1].ordered != ordered:
                stack.pop()                          # andere Art auf derselben Ebene: neue Liste
            if not stack or stack[-1][0] < depth:
                new = ListBlock(ordered)
                if stack and stack[-1][1].items:
                    parent_item = stack[-1][1].items[-1]
                    if parent_item.sub is None:
                        parent_item.sub = new
                    else:
                        new = parent_item.sub
                elif not stack:
                    blocks.append(new)
                stack.append((depth, new))
            stack[-1][1].items.append(ListItem(item.group(3).strip()))
            continue
        if not line.strip():
            end_paragraph()
            end_list()
            continue
        if heading_level(line):
            end_paragraph()
            end_list()
            blocks.append(Heading(heading_level(line), strip_heading(line).strip()))
            continue
        end_list()
        paragraph.append(line.rstrip())
    end_paragraph()
    return blocks
