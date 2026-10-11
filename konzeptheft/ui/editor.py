"""Textfeld für den geöffneten Abschnitt.

Escape meldet closeRequested, das Hauptfenster springt dann zurück in die Liste. Überschriften
stehen im Text als Markdown-Zeichen am Zeilenanfang ("# " ist Ebene 1), damit der Screenreader
immer mitliest, dass es eine Überschrift ist.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor

from konzeptheft.core.concept import Section, set_heading, strip_heading
from konzeptheft.ui.common import PlainEdit, name_widget

CLOSED_NAME = "Text, kein Abschnitt geöffnet"


class SectionEditor(PlainEdit):
    closeRequested = Signal()

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
        if event.key() == Qt.Key.Key_Escape and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.closeRequested.emit()
            return
        super().keyPressEvent(event)

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
