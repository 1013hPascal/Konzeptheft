"""Rechtschreibung: Fehler finden, Vorschläge, die Liste "Meine Wörter".

Die eigentliche Prüfung macht ein Prüfer mit check(text) und suggest(word), normalerweise
WindowsSpellChecker (windows_spelling.py). In den Tests ersetzt ein erfundener Prüfer ihn.

Positionen beziehen sich immer auf den Text eines Abschnitts, so wie er im Konzept steht
(ohne die Platzhalter für leere Zeilen aus dem Textfeld).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from konzeptheft.core.windows_spelling import ACTION_DELETE, RawError

log = logging.getLogger(__name__)

DELETE_WORD = "Doppeltes Wort löschen"


class Checker(Protocol):
    def check(self, text: str) -> list[RawError]: ...
    def suggest(self, word: str) -> list[str]: ...


@dataclass(frozen=True)
class SpellError:
    start: int
    length: int
    word: str
    repeated: bool = False                 # doppeltes Wort, zum Beispiel "und und"

    @property
    def end(self) -> int:
        return self.start + self.length


class MyWords:
    """Wörter, die der Nutzer ins Wörterbuch übernommen hat. Eine Datei, ein Wort pro Zeile."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._words: set[str] = set()
        if path is not None:
            try:
                self._words = {w.strip() for w in path.read_text(encoding="utf-8").splitlines()
                               if w.strip()}
            except OSError:
                pass

    def __contains__(self, word: str) -> bool:
        return word in self._words or word.lower() in {w.lower() for w in self._words}

    def words(self) -> list[str]:
        return sorted(self._words, key=str.lower)

    def add(self, word: str) -> None:
        word = word.strip()
        if word and word not in self._words:
            self._words.add(word)
            self._save()

    def remove(self, words: list[str]) -> None:
        if self._words & set(words):
            self._words -= set(words)
            self._save()

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("".join(f"{w}\n" for w in self.words()), encoding="utf-8")
        except OSError as exc:
            log.warning("Meine Wörter nicht gespeichert: %s", exc)


class Spelling:
    """Prüfer und "Meine Wörter" zusammen."""

    def __init__(self, checker: Checker, my_words: MyWords) -> None:
        self.checker = checker
        self.my_words = my_words

    def errors(self, text: str) -> list[SpellError]:
        found = []
        offset = 0
        for line in text.split("\n"):                  # zeilenweise: Windows sieht keine Absätze
            for raw in self._check(line):
                word = line[raw.start:raw.start + raw.length]
                repeated = raw.action == ACTION_DELETE
                if not word.strip() or (not repeated and word in self.my_words):
                    continue
                found.append(SpellError(offset + raw.start, raw.length, word, repeated))
            offset += len(line) + 1
        return found

    def _check(self, line: str) -> list[RawError]:
        try:
            return self.checker.check(line)
        except OSError as exc:
            log.warning("Rechtschreibprüfung: %s", exc)
            return []

    def suggestions(self, error: SpellError) -> list[str]:
        if error.repeated:
            return [DELETE_WORD]
        try:
            return [s for s in self.checker.suggest(error.word) if s != error.word]
        except OSError as exc:
            log.warning("Vorschläge: %s", exc)
            return []

    def error_at(self, text: str, position: int) -> SpellError | None:
        """Der Fehler, in dem position liegt oder an dessen Ende sie steht."""
        for error in self.errors(text):
            if error.start <= position <= error.end:
                return error
        return None


def fix_range(text: str, error: SpellError, replacement: str | None) -> tuple[int, int, str]:
    """Was ersetzt wird: (Anfang, Ende, neuer Text). replacement None löscht ein doppeltes Wort
    samt Leerzeichen davor."""
    if replacement is None:
        start = error.start
        while start > 0 and text[start - 1] in " \t":
            start -= 1
        return start, error.end, ""
    return error.start, error.end, replacement


def apply_fix(text: str, error: SpellError, replacement: str | None) -> tuple[str, int]:
    """Neuer Text und die Stelle hinter der Änderung."""
    start, end, insert = fix_range(text, error, replacement)
    return text[:start] + insert + text[end:], start + len(insert)


def word_end_errors(spelling: Spelling, line: str, end: int) -> bool:
    """Ist das Wort, das in line genau an Stelle end endet, falsch? Für den Ton beim Tippen."""
    return any(e.end == end and not e.repeated for e in spelling.errors(line))
