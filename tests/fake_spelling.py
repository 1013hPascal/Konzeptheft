"""Erfundener Prüfer für die Tests: kennt ein paar falsche Wörter und doppelte Wörter."""
from __future__ import annotations

import re

from konzeptheft.core.windows_spelling import ACTION_DELETE, ACTION_SUGGEST, RawError

SUGGESTIONS = {"Tset": ["Test", "Stet"], "Fehlrn": ["Fehlern", "Fehler"], "Konzpt": ["Konzept"],
               "Wortt": ["Wort"]}


class FakeChecker:
    def __init__(self) -> None:
        self.calls = 0

    def check(self, text: str) -> list[RawError]:
        self.calls += 1
        errors = []
        previous = None
        for match in re.finditer(r"\w+", text):
            word = match.group(0)
            if word in SUGGESTIONS or word.startswith("Falsch"):
                errors.append(RawError(match.start(), len(word), ACTION_SUGGEST, ""))
            elif previous is not None and word == previous:
                errors.append(RawError(match.start(), len(word), ACTION_DELETE, ""))
            previous = word
        return errors

    def suggest(self, word: str) -> list[str]:
        return SUGGESTIONS.get(word, [])
