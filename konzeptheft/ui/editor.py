"""Textfeld für den geöffneten Abschnitt.

Escape meldet closeRequested, das Hauptfenster springt dann zurück in die Liste. Überschriften
stehen im Text als Markdown-Zeichen am Zeilenanfang ("# " ist Ebene 1), damit der Screenreader
immer mitliest, dass es eine Überschrift ist.

Für die Rechtschreibung meldet das Textfeld zwei Signale (spelling_ui.py hört zu):
- wordFinished(Zeile, Spalte): Ein Wort ist zu Ende getippt (Leerzeichen, Satzzeichen, Enter).
- navigated(Art): Der Cursor ging mit der Tastatur in eine andere Zeile ("line") oder mit
  Strg+Pfeil zu einem anderen Wort ("word").
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor

from konzeptheft.core.concept import Section, set_heading, strip_heading
from konzeptheft.ui.common import EMPTY_LINE, PlainEdit, name_widget

CLOSED_NAME = "Text, kein Abschnitt geöffnet"
NEWLINE = chr(10)
WORD_END = set(" .,;:!?)]}\"'") | {chr(9)}         # Zeichen, die ein Wort beenden (mit Tab)
LINE_KEYS = {Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown}


class SectionEditor(PlainEdit):
    closeRequested = Signal()
    wordFinished = Signal(int, int)
    navigated = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.section: Section | None = None         # der geöffnete Abschnitt
        self.setLineWrapMode(PlainEdit.LineWrapMode.WidgetWidth)
        self.setPlaceholderText("Enter auf einem Abschnitt öffnet hier seinen Text.")
        self.close_section()

    def open_section(self, section: Section, name: str) -> None:
        """name: was der Screenreader hört, zum Beispiel "3.1 Teil"."""
        self.section = section
        self.blockSignals(True)
        self.set_text(section.text)
        self.blockSignals(False)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self._keep_before_placeholder()
        self.set_name(name)
        self.setEnabled(True)

    def close_section(self) -> None:
        self.section = None
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)
        name_widget(self, CLOSED_NAME)
        self.setEnabled(False)

    def set_name(self, name: str) -> None:
        name_widget(self, f"Text von {name}")

    def keyPressEvent(self, event) -> None:
        key, modifiers = event.key(), event.modifiers()
        if key == Qt.Key.Key_Escape and modifiers == Qt.KeyboardModifier.NoModifier:
            self.closeRequested.emit()
            return
        before = self.textCursor()
        typed = event.text()
        ends_word = not before.hasSelection() and (
            key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) or (bool(typed) and typed in WORD_END))
        row, column = before.blockNumber(), before.positionInBlock()
        super().keyPressEvent(event)
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        if ends_word:
            self.wordFinished.emit(row, column)
        elif key in LINE_KEYS or (ctrl and key in (Qt.Key.Key_Home, Qt.Key.Key_End)):
            self.navigated.emit("line")
        elif ctrl and key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.navigated.emit("word")

    # -- Stellen im Abschnittstext ----------------------------------------------------------
    def section_offset(self, position: int) -> int:
        """Stelle im Dokument -> Stelle im Text des Abschnitts (ohne Platzhalter leerer Zeilen)."""
        block = self.document().findBlock(position)
        lines = self.text().split(NEWLINE)[:block.blockNumber()]
        offset = sum(len(line) + 1 for line in lines)
        column = position - block.position()
        return offset + (0 if block.text() == EMPTY_LINE else column)

    def document_position(self, offset: int) -> int:
        """Stelle im Text des Abschnitts -> Stelle im Dokument."""
        text = self.text()
        row = text[:offset].count(NEWLINE)
        column = offset - (text.rfind(NEWLINE, 0, offset) + 1)
        block = self.document().findBlockByNumber(row)
        return block.position() + (0 if block.text() == EMPTY_LINE else column)

    def replace_range(self, start: int, end: int, text: str) -> None:
        """Teil des Abschnittstexts ersetzen, mit Rückgängig und Platzhaltern."""
        cursor = QTextCursor(self.document())
        cursor.setPosition(self.document_position(start))
        cursor.setPosition(self.document_position(end), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)

    def set_heading(self, level: int) -> None:
        """Macht die Zeile mit dem Cursor zur Überschrift (Ebene 0: normaler Text). Der Cursor
        bleibt an derselben Stelle im Text der Zeile."""
        cursor = self.textCursor()
        block = cursor.block()
        old = block.text()
        new = set_heading(old, level)
        if new == old:
            return
        offset = cursor.positionInBlock() + len(new) - len(old)
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(new)
        cursor.endEditBlock()
        prefix = len(new) - len(strip_heading(new))
        cursor.setPosition(block.position() + max(prefix, min(offset, len(new))))
        self.setTextCursor(cursor)
