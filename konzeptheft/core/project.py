"""Projektdatei (.konzept): hält den ganzen Baum mit Unterlisten fest.

Inhalt ist JSON in UTF-8, gut lesbar eingerückt:
{"format": "konzeptheft", "version": 1, "title": "...",
 "sections": [{"name": "...", "text": "...", "children": [...]}]}
"""
from __future__ import annotations

import json

from konzeptheft.core.concept import MAX_DEPTH, Concept, Section, clean_name

SUFFIX = ".konzept"
FORMAT = "konzeptheft"
VERSION = 1


class ProjectFormatError(ValueError):
    """Die Datei ist keine gültige Konzeptheft-Datei."""


def _section_to_dict(section: Section) -> dict:
    data = {"name": section.name, "text": section.text}
    if section.children:
        data["children"] = [_section_to_dict(child) for child in section.children]
    return data


def to_json(concept: Concept) -> str:
    data = {"format": FORMAT, "version": VERSION, "title": concept.title,
            "sections": [_section_to_dict(s) for s in concept.sections]}
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _section_from_dict(data: object, depth: int) -> Section:
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        raise ProjectFormatError("Ein Abschnitt hat keinen Namen.")
    text = data.get("text", "")
    children = data.get("children", [])
    if not isinstance(text, str) or not isinstance(children, list):
        raise ProjectFormatError(f"Abschnitt „{data['name']}“ ist beschädigt.")
    if children and depth >= MAX_DEPTH:
        raise ProjectFormatError("Die Datei hat mehr als vier Unterebenen.")
    return Section(clean_name(data["name"]) or "Ohne Namen", text.replace("\r\n", "\n"),
                   [_section_from_dict(child, depth + 1) for child in children])


def from_json(source: str, fallback_title: str = "") -> Concept:
    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ProjectFormatError("Die Datei ist keine Konzeptheft-Datei.") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ProjectFormatError("Die Datei ist keine Konzeptheft-Datei.")
    if not isinstance(data.get("version"), int) or data["version"] > VERSION:
        raise ProjectFormatError("Die Datei stammt von einer neueren Version des Konzepthefts.")
    sections = data.get("sections", [])
    if not isinstance(sections, list):
        raise ProjectFormatError("Die Abschnitte sind beschädigt.")
    title = data.get("title") if isinstance(data.get("title"), str) else ""
    concept = Concept(title or fallback_title, [_section_from_dict(s, 0) for s in sections])
    concept.modified = False
    return concept
