"""Ausgabe für andere Leser: reiner Text und HTML für die PDF.

Die Namen der Abschnitte werden Überschriften: Hauptebene Ebene 1, erste Unterebene Ebene 2
und so weiter bis Ebene 5. Überschriften im Text eines Abschnitts (Alt+1 bis Alt+3) liegen eine
Ebene unter dem Abschnitt, höchstens Ebene 6.
"""
from __future__ import annotations

from html import escape

from konzeptheft.core.concept import Concept, export_number, heading_level, strip_heading

MAX_HTML_HEADING = 6


def to_plain_text(concept: Concept) -> str:
    """Reiner Text ohne Markdown-Zeichen. Die Nummern zeigen die Ebene."""
    parts = []
    if concept.title:
        parts += [concept.title, ""]
    for numbers, section in concept.walk():
        parts += [f"{export_number(numbers)} {section.name}", ""]
        body = "\n".join(strip_heading(line) for line in section.text.splitlines()).strip("\n")
        if body.strip():
            parts += [body, ""]
    return "\n".join(parts).rstrip("\n") + "\n"


def _body_html(text: str, depth: int) -> list[str]:
    """Absätze und Überschriften aus dem Text eines Abschnitts. depth 0 ist die Hauptebene."""
    html: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            html.append("<p>" + "<br>".join(paragraph) + "</p>")
            paragraph.clear()

    for line in text.splitlines():
        level = heading_level(line)
        if level:
            flush()
            tag = f"h{min(MAX_HTML_HEADING, depth + 1 + level)}"
            html.append(f"<{tag}>{escape(strip_heading(line))}</{tag}>")
        elif line.strip():
            paragraph.append(escape(line))
        else:
            flush()
    flush()
    return html


def to_html(concept: Concept) -> str:
    """HTML für die PDF. Der Titel steht groß über allem, ist aber keine Überschrift, damit die
    Abschnitte der Hauptebene Überschrift Ebene 1 sind."""
    html = ["<html><body>"]
    if concept.title:
        html.append(f'<p style="font-size:22pt; font-weight:bold">{escape(concept.title)}</p>')
    for numbers, section in concept.walk():
        depth = len(numbers) - 1
        tag = f"h{depth + 1}"
        html.append(f"<{tag}>{escape(export_number(numbers))} {escape(section.name)}</{tag}>")
        html += _body_html(section.text, depth)
    html.append("</body></html>")
    return "\n".join(html)
