"""Datenmodell: Ein Konzept hat einen Titel und eine Liste von Abschnitten. Jeder Abschnitt kann
eine Unterliste haben, bis zu MAX_SUBLEVELS Unterebenen tief.

Die Nummern werden nicht gespeichert. Sie ergeben sich immer aus der Position und stimmen
deshalb nach jedem Einfügen, Verschieben oder Löschen. In der Liste steht für jede Unterebene, die
es unter einem Abschnitt gibt, ein ".0" am Ende (Wunsch vom 08.10.2026): "3" ohne Unterliste,
"3.0" mit einer Unterebene, "3.0.0" mit zwei. Auf der ersten Unterebene "3.1", "3.1.0" und so weiter.

Abschnitte werden über das Objekt selbst angesprochen (nicht über die Position), damit das
geöffnete Textfeld beim Verschieben und Einfügen am richtigen Abschnitt bleibt. Deshalb
vergleicht Section mit "is" (eq=False).
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

MAX_SUBLEVELS = 4                     # Hauptliste plus vier Unterlisten
MAX_DEPTH = MAX_SUBLEVELS             # Tiefe 0 ist die Hauptliste
MAX_HEADING_LEVEL = 3
_HEADING = re.compile(r"^(#+)(?:[ \t]+|$)")


@dataclass(eq=False)
class Section:
    name: str
    text: str = ""
    children: list[Section] = field(default_factory=list)

    def count_all(self) -> int:
        """Anzahl aller Untereinträge, auf allen Ebenen."""
        return sum(1 + child.count_all() for child in self.children)

    def sublevels(self) -> int:
        """Wie viele Unterebenen es unter diesem Abschnitt gibt (0 ohne Unterliste)."""
        return 1 + max(child.sublevels() for child in self.children) if self.children else 0


def number_text(numbers: list[int], sublevels: int) -> str:
    """Nummer für die Liste: "3", "3.0" (eine Unterebene), "3.0.0" (zwei), "3.1", "3.1.0"."""
    return ".".join(str(n) for n in numbers) + ".0" * sublevels


def export_number(numbers: list[int]) -> str:
    """Nummer für PDF und Text: "3." auf der Hauptebene, sonst "3.1" (ohne ".0")."""
    text = ".".join(str(n) for n in numbers)
    return text + "." if len(numbers) == 1 else text


class Concept:
    def __init__(self, title: str = "", sections: list[Section] | None = None) -> None:
        self._title = title
        self.sections: list[Section] = list(sections or [])
        self.modified = False

    # -- Titel ------------------------------------------------------------------------------
    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        value = value.strip()
        if value != self._title:
            self._title = value
            self.modified = True

    def __len__(self) -> int:
        return len(self.sections)

    # -- Baum ---------------------------------------------------------------------------------
    def children_of(self, parent: Section | None) -> list[Section]:
        """Die Liste einer Ebene. parent None ist die Hauptliste."""
        return self.sections if parent is None else parent.children

    def walk(self) -> Iterator[tuple[list[int], Section]]:
        """Alle Abschnitte von oben nach unten, mit ihren Nummern, zum Beispiel [3, 1]."""
        def visit(items: list[Section], prefix: list[int]):
            for position, section in enumerate(items, start=1):
                numbers = prefix + [position]
                yield numbers, section
                yield from visit(section.children, numbers)
        yield from visit(self.sections, [])

    def numbers_of(self, section: Section) -> list[int] | None:
        """Nummern des Abschnitts, None wenn er nicht (mehr) im Konzept ist."""
        for numbers, candidate in self.walk():
            if candidate is section:
                return numbers
        return None

    def contains(self, section: Section) -> bool:
        return self.numbers_of(section) is not None

    def label(self, section: Section) -> str:
        """Eintrag in der Liste, sichtbar und für den Screenreader gleich: "3.0 Lösung".
        Kein "3 von 5" mehr (Wunsch vom 08.10.2026)."""
        numbers = self.numbers_of(section) or [0]
        return f"{number_text(numbers, section.sublevels())} {section.name}"

    def parent_of(self, section: Section) -> Section | None:
        for _numbers, candidate in self.walk():
            if any(child is section for child in candidate.children):
                return candidate
        return None

    # -- Ändern -------------------------------------------------------------------------------
    def add(self, name: str, parent: Section | None = None) -> int:
        """Neuer Abschnitt am Ende der Ebene. Gibt seinen Index zurück."""
        items = self.children_of(parent)
        items.append(Section(clean_name(name)))
        self.modified = True
        return len(items) - 1

    def insert_after(self, index: int, name: str, parent: Section | None = None) -> int:
        """Neuer Abschnitt direkt unter index. index -1 bedeutet: ganz an den Anfang."""
        items = self.children_of(parent)
        position = max(0, min(index + 1, len(items)))
        items.insert(position, Section(clean_name(name)))
        self.modified = True
        return position

    def move(self, index: int, delta: int, parent: Section | None = None) -> int | None:
        """Verschiebt innerhalb der Ebene. Gibt den neuen Index zurück, None am Rand."""
        items = self.children_of(parent)
        target = index + delta
        if not (0 <= index < len(items)) or not (0 <= target < len(items)):
            return None
        items.insert(target, items.pop(index))
        self.modified = True
        return target

    def remove(self, index: int, parent: Section | None = None) -> Section:
        """Löscht den Abschnitt samt Unterliste."""
        section = self.children_of(parent).pop(index)
        self.modified = True
        return section

    def rename(self, section: Section, name: str) -> None:
        name = clean_name(name)
        if name != section.name:
            section.name = name
            self.modified = True

    def set_text(self, section: Section, text: str) -> None:
        if text != section.text:
            section.text = text
            self.modified = True


def clean_name(name: str) -> str:
    """Namen sind einzeilig und ohne Leerzeichen am Rand."""
    return " ".join(name.split())


# -- Überschriften im Text ------------------------------------------------------------------
def heading_level(line: str) -> int:
    """Ebene der Überschrift im Textfeld (Anzahl der #), 0 bei normalem Text."""
    match = _HEADING.match(line)
    return len(match.group(1)) if match else 0


def strip_heading(line: str) -> str:
    """Zeile ohne Markdown-Zeichen für Überschriften."""
    match = _HEADING.match(line)
    return line[match.end():] if match else line


def set_heading(line: str, level: int) -> str:
    """Macht die Zeile zur Überschrift der Ebene level. Ebene 0 ergibt normalen Text."""
    body = strip_heading(line)
    return f"{'#' * level} {body}" if level > 0 else body
