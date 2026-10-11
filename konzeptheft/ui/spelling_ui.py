"""Rechtschreibung in der Oberfläche (Wunsch vom 11.10.2026).

- Falsche Wörter sind rot gewellt unterstrichen (QSyntaxHighlighter).
- Ist ein Wort fertig getippt und falsch, kommt ein kurzer Ton, wie in Word.
- Qt gibt Rechtschreibfehler nicht an NVDA weiter (geprüft im Quelltext von Qt 6.11). Deshalb
  sagt das Programm selbst an: beim Wechsel in eine Zeile mit Fehlern "Fehler: Wort, Wort", bei
  Strg+Pfeil auf ein falsches Wort "Rechtschreibfehler", beim Öffnen eines Abschnitts die Anzahl.
- Alt+R: Dialog für das Wort am Cursor. Alt+Umschalt+R: Dialog für das ganze Konzept.
- Meine Wörter: Wörter, die man ins Wörterbuch übernommen hat. Im Dialog als Liste mit
  Kontrollkästchen. Ein abgewähltes Wort wird beim Schließen oder bei Weiter gelöscht.

Der Ton ist eine kleine WAV-Datei, die einmal erzeugt und mit winsound ohne Warten abgespielt
wird. So stockt das Tippen nicht, und es braucht keine neue Bibliothek.
"""
from __future__ import annotations

import io
import logging
import math
import struct
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QDialogButtonBox, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout, QWidget)

from konzeptheft.core.concept import Section
from konzeptheft.core.spelling import DELETE_WORD, SpellError, Spelling, fix_range, word_end_errors
from konzeptheft.ui.announcer import announce
from konzeptheft.ui.common import EMPTY_LINE, FocusDialog, announce_focus, label_for, name_widget

if TYPE_CHECKING:
    from konzeptheft.ui.main_window import MainWindow

log = logging.getLogger(__name__)

NO_SUGGESTIONS = "Keine Vorschläge"
ENABLED_KEY, SOUND_KEY, SPEAK_KEY = "spelling/enabled", "spelling/sound", "spelling/speak"


# -- Ton ------------------------------------------------------------------------------------------
_sound_file: Path | None = None


def _make_sound() -> Path:
    """Kurzer, weicher Doppelton (90 ms), leiser als die Systemklänge."""
    rate, samples = 22050, []
    for frequency, duration in ((660, 0.045), (440, 0.045)):
        count = int(rate * duration)
        for i in range(count):
            fade = min(1.0, i / 200, (count - i) / 200)
            samples.append(int(9000 * fade * math.sin(2 * math.pi * frequency * i / rate)))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    path = Path(tempfile.gettempdir()) / "konzeptheft-tippfehler.wav"
    path.write_bytes(buffer.getvalue())
    return path


def _play_error_sound() -> None:
    global _sound_file
    try:
        if sys.platform != "win32":
            from PySide6.QtWidgets import QApplication
            QApplication.beep()
            return
        import winsound
        if _sound_file is None or not _sound_file.is_file():
            _sound_file = _make_sound()
        winsound.PlaySound(str(_sound_file), winsound.SND_FILENAME | winsound.SND_ASYNC
                           | winsound.SND_NODEFAULT)
    except Exception as exc:                          # noqa: BLE001 (Ton ist nur Zusatz)
        log.warning("Ton nicht abgespielt: %r", exc)


play_error_sound: Callable[[], None] = _play_error_sound        # in Tests ersetzbar


# -- Unterstreichen ---------------------------------------------------------------------------------
class SpellHighlighter(QSyntaxHighlighter):
    def __init__(self, document, spelling: Spelling) -> None:
        super().__init__(document)
        self.spelling = spelling
        self.enabled = True
        self.format = QTextCharFormat()
        self.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.format.setUnderlineColor(QColor(Qt.GlobalColor.red))

    def highlightBlock(self, text: str) -> None:
        if not self.enabled or not text or text == EMPTY_LINE:
            return
        for error in self.spelling.errors(text):
            self.setFormat(error.start, error.length, self.format)


# -- Dialog -----------------------------------------------------------------------------------------
@dataclass
class Found:
    """Ein Fehler im Dialog: wo er steht und was angezeigt wird."""
    section: Section
    error: SpellError
    where: str                      # zum Beispiel "3.1 Teil"
    context: str                    # die Zeile um das Wort


class SpellDialog(FocusDialog):
    """Feld mit dem Wort, Vorschläge mit Kontrollkästchen, Weiter, In Wörterbuch übernehmen,
    Schließen, Meine Wörter. Ohne Fehler (words_only) nur Meine Wörter und Schließen.

    advance(entscheidung) liefert den nächsten Fehler oder None, dann schließt der Dialog.
    Entscheidung: ("replace", Text), ("delete", None), ("skip", None), ("add", Text)."""

    def __init__(self, spelling: Spelling, advance: Callable[[tuple[str, str | None]], Found | None],
                 parent: QWidget | None = None, words_only: bool = False) -> None:
        super().__init__(parent)
        self.spelling = spelling
        self.advance = advance
        self.current: Found | None = None
        self.setWindowTitle("Meine Wörter" if words_only else "Rechtschreibung")

        self.field = QLineEdit()
        self.context = QLabel()
        self.context.setWordWrap(True)
        self.suggestions = QListWidget()
        self.next_button = QPushButton("&Weiter")
        self.add_button = QPushButton("In Wörter&buch übernehmen")
        self.close_button = QPushButton("&Schließen")
        self.words = QListWidget()

        layout = QVBoxLayout(self)
        self.field_label = label_for(self.field, "&Wort:")
        layout.addWidget(self.field_label)
        layout.addWidget(self.field)
        layout.addWidget(self.context)
        self.suggestions_label = label_for(self.suggestions, "&Vorschläge:")
        layout.addWidget(self.suggestions_label)
        layout.addWidget(self.suggestions)
        buttons = QDialogButtonBox()
        for button in (self.next_button, self.add_button, self.close_button):
            buttons.addButton(button, QDialogButtonBox.ButtonRole.ActionRole)
        layout.addWidget(buttons)
        layout.addWidget(label_for(self.words, "&Meine Wörter:"))
        layout.addWidget(self.words)
        for first, second in ((self.field, self.suggestions), (self.suggestions, self.next_button),
                              (self.next_button, self.add_button),
                              (self.add_button, self.close_button),
                              (self.close_button, self.words)):
            self.setTabOrder(first, second)

        self.next_button.clicked.connect(self.next_clicked)
        self.add_button.clicked.connect(self.add_clicked)
        self.close_button.clicked.connect(self.reject)
        self.suggestions.itemChanged.connect(self._only_one_checked)
        self.fill_words()

        if words_only:
            for widget in (self.field_label, self.field, self.context, self.suggestions_label,
                           self.suggestions, self.next_button, self.add_button):
                widget.hide()
            self.close_button.setDefault(True)
            self.initial_focus_widget = self.words
        else:
            self.next_button.setDefault(True)
            self.initial_focus_widget = self.field
        self.resize(560, 520)

    # -- Inhalt ---------------------------------------------------------------------------
    def show_found(self, found: Found) -> None:
        self.current = found
        self.setWindowTitle(f"Rechtschreibung – {found.where}")
        self.field.setText(found.error.word)
        self.field.selectAll()
        self.context.setText(f"In {found.where}: {found.context}")
        self.suggestions.blockSignals(True)
        self.suggestions.clear()
        options = self.spelling.suggestions(found.error)
        for text in options or [NO_SUGGESTIONS]:
            item = QListWidgetItem(text)
            if options:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            self.suggestions.addItem(item)
        self.suggestions.setCurrentRow(0)
        self.suggestions.blockSignals(False)
        if self.isVisible():
            self.field.setFocus()
            announce_focus(self.field)

    def fill_words(self) -> None:
        self.words.clear()
        for word in self.spelling.my_words.words():
            item = QListWidgetItem(word)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.words.addItem(item)
        if self.words.count():
            self.words.setCurrentRow(0)

    def _only_one_checked(self, changed: QListWidgetItem) -> None:
        """Wie Optionsfelder: Es ist höchstens ein Vorschlag angehakt."""
        if changed.checkState() != Qt.CheckState.Checked:
            return
        self.suggestions.blockSignals(True)
        for row in range(self.suggestions.count()):
            item = self.suggestions.item(row)
            if item is not changed and item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.suggestions.blockSignals(False)

    def checked_suggestion(self) -> str | None:
        for row in range(self.suggestions.count()):
            item = self.suggestions.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                return item.text()
        return None

    # -- Knöpfe ---------------------------------------------------------------------------
    def apply_word_removals(self) -> None:
        """Abgewählte Wörter aus Meine Wörter löschen."""
        removed = [self.words.item(r).text() for r in range(self.words.count())
                   if self.words.item(r).checkState() != Qt.CheckState.Checked]
        if removed:
            self.spelling.my_words.remove(removed)
            self.fill_words()
            announce(f"{len(removed)} Wort aus Meine Wörter gelöscht" if len(removed) == 1
                     else f"{len(removed)} Wörter aus Meine Wörter gelöscht")

    def decision(self) -> tuple[str, str | None]:
        if self.current is None:
            return "skip", None
        chosen = self.checked_suggestion()
        if chosen == DELETE_WORD and self.current.error.repeated:
            return "delete", None
        if chosen is not None:
            return "replace", chosen
        typed = self.field.text().strip()
        if typed and typed != self.current.error.word:
            return "replace", typed
        return "skip", None

    def next_clicked(self) -> None:
        self.apply_word_removals()
        self._go(self.decision())

    def add_clicked(self) -> None:
        typed = self.field.text().strip()
        if not typed:
            return
        self.apply_word_removals()
        self._go(("add", typed))
        self.fill_words()

    def _go(self, decision: tuple[str, str | None]) -> None:
        following = self.advance(decision)
        if following is None:
            self.accept()
        else:
            self.show_found(following)

    def reject(self) -> None:
        self.apply_word_removals()
        super().reject()


# -- Steuerung --------------------------------------------------------------------------------------
class SpellSupport(QObject):
    """Verbindet Rechtschreibung, Textfeld und Hauptfenster."""

    def __init__(self, window: "MainWindow", spelling: Spelling | None) -> None:
        super().__init__(window)
        self.window = window
        self.spelling = spelling
        self.settings = window.settings
        self.highlighter: SpellHighlighter | None = None
        if spelling is not None:
            self.highlighter = SpellHighlighter(window.editor.document(), spelling)
            self.highlighter.enabled = self.enabled
            window.editor.wordFinished.connect(self.word_finished)
            window.editor.navigated.connect(self.navigated)

    # -- Einstellungen --------------------------------------------------------------------
    def _flag(self, key: str) -> bool:
        return str(self.settings.value(key, "true")).lower() == "true"

    @property
    def enabled(self) -> bool:
        return self._flag(ENABLED_KEY)

    def set_flag(self, key: str, value: bool) -> None:
        self.settings.setValue(key, "true" if value else "false")
        if key == ENABLED_KEY and self.highlighter is not None:
            self.highlighter.enabled = value
            self.highlighter.rehighlight()

    @property
    def active(self) -> bool:
        return self.spelling is not None and self.enabled

    def _unavailable(self) -> bool:
        if self.spelling is None:
            announce("Windows hat keine deutsche Rechtschreibprüfung. Sie lässt sich in den "
                     "Windows-Einstellungen unter Sprache mit dem deutschen Sprachpaket "
                     "installieren.")
            return True
        return False

    # -- Beim Tippen und Lesen -----------------------------------------------------------
    def word_finished(self, row: int, column: int) -> None:
        if not self.active or not self._flag(SOUND_KEY):
            return
        line = self.window.editor.document().findBlockByNumber(row).text()
        if line != EMPTY_LINE and word_end_errors(self.spelling, line, column):
            play_error_sound()

    def navigated(self, kind: str) -> None:
        if not self.active or not self._flag(SPEAK_KEY):
            return
        cursor = self.window.editor.textCursor()
        line = cursor.block().text()
        if line == EMPTY_LINE:
            return
        errors = self.spelling.errors(line)
        if kind == "line" and errors:
            announce("Fehler: " + ", ".join(e.word for e in errors))
        elif kind == "word":
            column = cursor.positionInBlock()
            if any(e.start <= column < e.end for e in errors):
                announce("Rechtschreibfehler")

    def section_opened(self, section: Section) -> None:
        if not self.active or not self._flag(SPEAK_KEY):
            return
        count = len(self.spelling.errors(section.text))
        if count:
            announce("1 Rechtschreibfehler" if count == 1 else f"{count} Rechtschreibfehler")

    # -- Dialoge --------------------------------------------------------------------------
    def _context(self, text: str, error: SpellError) -> str:
        line_start = text.rfind("\n", 0, error.start) + 1
        line_end = text.find("\n", error.end)
        line = text[line_start:line_end if line_end >= 0 else len(text)].strip()
        return line if len(line) <= 120 else line[:117] + "…"

    def _found(self, section: Section, error: SpellError) -> Found:
        return Found(section, error, self.window.concept.label(section),
                     self._context(section.text, error))

    def _apply(self, section: Section, error: SpellError, replacement: str | None) -> int:
        """Korrektur in den Text schreiben. Gibt die Stelle hinter der Änderung zurück."""
        start, end, insert = fix_range(section.text, error, replacement)
        editor = self.window.editor
        if editor.section is section:
            editor.replace_range(start, end, insert)        # löst die Übernahme ins Konzept aus
        else:
            self.window.concept.set_text(section, section.text[:start] + insert
                                         + section.text[end:])
        self.window.update_title()
        return start + len(insert)

    def _decide(self, found: Found, decision: tuple[str, str | None]) -> int:
        """Entscheidung umsetzen. Gibt die Stelle zurück, ab der weitergesucht wird."""
        kind, value = decision
        error = found.error
        if kind == "add":
            self.spelling.my_words.add(value or error.word)
            if value and value != error.word:
                return self._apply(found.section, error, value)
            return error.end
        if kind == "replace":
            return self._apply(found.section, error, value)
        if kind == "delete":
            return self._apply(found.section, error, None)
        return error.end

    def _finish(self) -> None:
        if self.highlighter is not None:
            self.highlighter.rehighlight()

    def check_word(self) -> None:
        """Alt+R: Fehler am Cursor im Textfeld."""
        if self._unavailable():
            return
        editor = self.window.editor
        if editor.section is None or self.window.focusWidget() is not editor:
            announce("Alt+R prüft das Wort im Textfeld. Alt+Umschalt+R prüft das ganze Konzept.")
            return
        section = editor.section
        offset = editor.section_offset(editor.textCursor().position())
        error = self.spelling.error_at(section.text, offset)
        if error is None:
            announce("Kein Rechtschreibfehler.")
            return
        found = self._found(section, error)

        def advance(decision: tuple[str, str | None]) -> Found | None:
            after = self._decide(found, decision)
            editor.setTextCursor(_cursor_at(editor, after))
            return None

        dialog = SpellDialog(self.spelling, advance, self.window)
        dialog.show_found(found)
        dialog.exec()
        self._finish()
        editor.setFocus()

    def check_concept(self) -> None:
        """Alt+Umschalt+R: alle Fehler im ganzen Konzept, Abschnitt für Abschnitt."""
        if self._unavailable():
            return
        sections = [section for _numbers, section in self.window.concept.walk()]
        state = {"index": 0, "offset": 0}

        def find_next() -> Found | None:
            while state["index"] < len(sections):
                section = sections[state["index"]]
                for error in self.spelling.errors(section.text):
                    if error.start >= state["offset"]:
                        return self._found(section, error)
                state["index"] += 1
                state["offset"] = 0
            return None

        first = find_next()
        if first is None:
            announce("Keine Rechtschreibfehler.")
            return
        current = {"found": first}

        def advance(decision: tuple[str, str | None]) -> Found | None:
            state["offset"] = self._decide(current["found"], decision)
            following = find_next()
            current["found"] = following
            if following is None:
                announce("Rechtschreibprüfung abgeschlossen.")
            return following

        focus = self.window.focusWidget()
        dialog = SpellDialog(self.spelling, advance, self.window)
        dialog.show_found(first)
        dialog.exec()
        self._finish()
        if focus is not None:
            focus.setFocus()

    def edit_my_words(self) -> None:
        if self._unavailable():
            return
        focus = self.window.focusWidget()
        SpellDialog(self.spelling, lambda _d: None, self.window, words_only=True).exec()
        self._finish()
        if focus is not None:
            focus.setFocus()


def _cursor_at(editor, offset: int):
    cursor = editor.textCursor()
    cursor.setPosition(editor.document_position(min(offset, len(editor.text()))))
    return cursor
