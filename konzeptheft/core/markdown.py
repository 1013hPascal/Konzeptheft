"""Öffnen von Markdown-Dateien (.md), zum Beispiel aus der ersten Version des Konzepthefts.

Aufbau: erste Zeile "# Titel", jeder Abschnitt beginnt mit "## Name". Überschriften im Text
stehen als "### " (Ebene 1) bis "##### " (Ebene 3). Im Textfeld werden daraus "# " bis "### ".
Eine .md-Datei hat keine Unterlisten. Gespeichert wird immer als .konzept (project.py).
"""
from __future__ import annotations

import re

from konzeptheft.core.concept import Concept, Section, heading_level

SECTION_SHIFT = 2                       # Abschnitte sind "##", Text-Überschriften liegen darunter
UNNAMED_SECTION = "Ohne Überschrift"
_TITLE = re.compile(r"^#[ \t]+(.*\S)[ \t]*$")
_SECTION = re.compile(r"^##[ \t]+(.*\S)[ \t]*$")


def _text_from_file(lines: list[str]) -> str:
    result = []
    for line in lines:
        if heading_level(line) > SECTION_SHIFT:
            line = line[SECTION_SHIFT:]
        result.append(line)
    while result and not result[0].strip():
        result.pop(0)
    while result and not result[-1].strip():
        result.pop()
    return "\n".join(result)


def from_markdown(source: str, fallback_title: str = "") -> Concept:
    """Erkennt die Abschnitte an den "## "-Zeilen. Text vor dem ersten Abschnitt (außer dem
    Titel) kommt in einen Abschnitt "Ohne Überschrift", damit nichts verloren geht."""
    title = ""
    sections: list[Section] = []
    name: str | None = None
    lines: list[str] = []
    seen_title = False

    def finish() -> None:
        text = _text_from_file(lines)
        if name is not None:
            sections.append(Section(name, text))
        elif text.strip():
            sections.append(Section(UNNAMED_SECTION, text))

    for line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        section_match = _SECTION.match(line)
        if section_match:
            finish()
            name, lines = section_match.group(1), []
            continue
        if name is None and not seen_title and not "".join(lines).strip():
            title_match = _TITLE.match(line)
            if title_match or line.strip() == "#":
                title = title_match.group(1) if title_match else ""
                seen_title = True
                continue
        lines.append(line)
    finish()
    concept = Concept(title or fallback_title, sections)
    concept.modified = False
    return concept
