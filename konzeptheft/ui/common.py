"""Kleine Hilfen für die Oberfläche (übernommen aus dem CodeCockpit)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAccessible, QAccessibleEvent, QTextCursor
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget)

REFOCUS_DELAY_MS = 80


class FocusDialog(QDialog):
    """Dialog, der seinen Startfokus erst nach dem Anzeigen setzt und NVDA meldet. Sonst zeigt
    die Braillezeile nach dem Öffnen noch den alten Fokus im Hauptfenster."""

    initial_focus_widget: QWidget | None = None

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(REFOCUS_DELAY_MS, self.refocus)

    def refocus(self) -> None:
        widget = self.initial_focus_widget
        if widget is None or not self.isVisible() or not widget.isVisible():
            return
        widget.setFocus()
        announce_focus(widget)


def announce_focus(widget: QWidget) -> None:
    """Fokus-Ereignis für NVDA senden, bei Listen für den markierten Eintrag."""
    event = QAccessibleEvent(widget, QAccessible.Event.Focus)
    if isinstance(widget, QAbstractItemView) and widget.currentIndex().isValid():
        event.setChild(widget.currentIndex().row())
    QAccessible.updateAccessibility(event)


def name_widget(widget: QWidget, name: str) -> None:
    """Namen für Screenreader setzen. Bewusst keine Beschreibung: Die Braillezeile zeigt sonst
    Name, Rolle und Beschreibung, und Tastenkürzel gehören nur ins Menü."""
    widget.setAccessibleName(name)


def label_for(widget: QWidget, text: str) -> QLabel:
    """Sichtbares Label mit Buddy. Der Accessible Name ist der Text ohne Doppelpunkt und &."""
    label = QLabel(text)
    label.setBuddy(widget)
    name_widget(widget, text.replace("&", "").rstrip(":").strip())
    return label


LINE_SEPARATOR = chr(0x2028)
PARAGRAPH_SEPARATOR = chr(0x2029)
EMPTY_LINE = chr(0xA0)            # geschütztes Leerzeichen, hält eine leere Zeile für NVDA fest


class PlainEdit(QPlainTextEdit):
    """Mehrzeiliges Textfeld für Screenreader und Braillezeile.

    - Tab wechselt den Fokus, statt ein Tabzeichen einzufügen.
    - Umschalt+Enter fügt einen echten Absatz ein. Qt fügt sonst den Zeilentrenner U+2028 ein, und
      die Braillezeile zeigt keine neue Zeile. Eingefügter Text wird ebenso bereinigt.

    Leere Zeilen (Rückmeldung vom 07.10.2026): Qt meldet NVDA über UI Automation für eine leere
    Zeile die Zeile davor. Nach Enter zeigte die Braillezeile deshalb noch die alte Zeile, bis man
    einen Buchstaben tippte. Qt sucht den Zeilenanfang rückwärts bis zu einem Zeichen, das kein
    Zeilenumbruch ist, und eine leere Zeile hat keines. Deshalb steht in jeder leeren Zeile intern
    ein geschütztes Leerzeichen (EMPTY_LINE). NVDA sagt dafür "leer". Der Cursor bleibt immer
    davor, wie in einer wirklich leeren Zeile. text() liefert den Text ohne diese Zeichen.
    Geschützte Leerzeichen am Anfang und Ende einer Zeile mit Text werden entfernt."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabChangesFocus(True)
        self._normalizing = False
        self.textChanged.connect(self._normalize)

    # -- Text ohne Platzhalter ----------------------------------------------------------------
    def set_text(self, text: str) -> None:
        lines = text.split("\n")
        if len(lines) > 1:
            lines = [line or EMPTY_LINE for line in lines]
        self.setPlainText("\n".join(lines))

    def text(self) -> str:
        """Der Text, wie der Nutzer ihn geschrieben hat (toPlainText macht aus geschützten
        Leerzeichen normale, deshalb Block für Block)."""
        lines = []
        block = self.document().begin()
        while block.isValid():
            line = block.text()
            lines.append("" if line == EMPTY_LINE else line)
            block = block.next()
        return "\n".join(lines)

    def _normalize(self) -> None:
        """Hält die Regel ein: leere Zeile = genau ein EMPTY_LINE, sonst keines am Rand."""
        if self._normalizing:
            return
        document = self.document()
        several = document.blockCount() > 1
        edits = []
        block = document.begin()
        while block.isValid():
            line = block.text()
            core = line.strip(EMPTY_LINE)
            if not core:
                if several and line != EMPTY_LINE:
                    edits.append((block.position(), len(line), EMPTY_LINE))
                elif not several and line:
                    edits.append((block.position(), len(line), ""))
            elif core != line:
                lead = len(line) - len(line.lstrip(EMPTY_LINE))
                trail = len(line) - len(line.rstrip(EMPTY_LINE))
                if trail:
                    edits.append((block.position() + len(line) - trail, trail, ""))
                if lead:
                    edits.append((block.position(), lead, ""))
            block = block.next()
        if not edits:
            return
        self._normalizing = True
        cursor = QTextCursor(document)
        cursor.joinPreviousEditBlock()            # Rückgängig nimmt Eingabe und Platzhalter zurück
        for position, length, replacement in sorted(edits, reverse=True):
            cursor.setPosition(position)
            cursor.setPosition(position + length, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(replacement)
        cursor.endEditBlock()
        self._normalizing = False
        self._keep_before_placeholder()

    def _on_placeholder(self, cursor: QTextCursor) -> bool:
        return not cursor.hasSelection() and cursor.block().text() == EMPTY_LINE

    def _keep_before_placeholder(self, forward: bool = False) -> None:
        """Steht der Cursor hinter dem Platzhalter, kommt er davor. forward (Pfeil rechts):
        stattdessen an den Anfang der nächsten Zeile."""
        cursor = self.textCursor()
        if not self._on_placeholder(cursor) or cursor.positionInBlock() == 0:
            return
        block = cursor.block()
        if forward and block.next().isValid():
            cursor.setPosition(block.next().position())
        else:
            cursor.setPosition(block.position())
        self.setTextCursor(cursor)

    # -- Tasten ---------------------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        key, modifiers = event.key(), event.modifiers()
        if (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.insertPlainText("\n")
            return
        cursor = self.textCursor()
        plain = modifiers in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.KeypadModifier)
        if plain and key == Qt.Key.Key_Delete and self._on_placeholder(cursor):
            # Entf in einer leeren Zeile entfernt die Zeile, die nächste rückt herauf
            if cursor.block().next().isValid():
                cursor.setPosition(cursor.block().position())
                cursor.setPosition(cursor.block().next().position(),
                                   QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                self.setTextCursor(cursor)
            return
        super().keyPressEvent(event)
        self._keep_before_placeholder(forward=plain and key == Qt.Key.Key_Right)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._keep_before_placeholder()

    def insertFromMimeData(self, source) -> None:
        if source.hasText():
            self.insertPlainText(source.text().replace(LINE_SEPARATOR, "\n")
                                 .replace(PARAGRAPH_SEPARATOR, "\n"))
        else:
            super().insertFromMimeData(source)

    def createMimeDataFromSelection(self):
        """Kopieren: ohne Platzhalter, mit echten Zeilenumbrüchen."""
        from PySide6.QtCore import QMimeData
        text = self.textCursor().selectedText().replace(PARAGRAPH_SEPARATOR, "\n")
        lines = ["" if not line.strip(EMPTY_LINE) else line for line in text.split("\n")]
        data = QMimeData()
        data.setText("\n".join(lines))
        return data


def ask_buttons(parent: QWidget | None, title: str, text: str, buttons: list[str],
                default: int, escape: int) -> int:
    """Rückfrage mit mehreren Antworten als Knöpfe. Gibt den Index des gewählten Knopfs zurück.
    default und escape sollten die sichere Antwort sein."""
    box = QMessageBox(QMessageBox.Icon.Question, title, text, QMessageBox.StandardButton.NoButton,
                      parent)
    added = [box.addButton(label, QMessageBox.ButtonRole.ActionRole) for label in buttons]
    box.setDefaultButton(added[default])
    box.setEscapeButton(added[escape])
    box.exec()
    clicked = box.clickedButton()
    return added.index(clicked) if clicked in added else escape


def show_info(parent: QWidget | None, title: str, text: str) -> None:
    box = QMessageBox(QMessageBox.Icon.Information, title, text,
                      QMessageBox.StandardButton.NoButton, parent)
    box.setEscapeButton(box.addButton("OK", QMessageBox.ButtonRole.AcceptRole))
    box.exec()


def show_error(parent: QWidget | None, title: str, text: str) -> None:
    box = QMessageBox(QMessageBox.Icon.Warning, title, text, QMessageBox.StandardButton.NoButton,
                      parent)
    box.setEscapeButton(box.addButton("OK", QMessageBox.ButtonRole.AcceptRole))
    box.exec()


class NameDialog(FocusDialog):
    """Fragt nach einem Namen. Enter bestätigt, Escape bricht ab. OK geht nur mit Text."""

    def __init__(self, title: str, label: str, text: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.edit = QLineEdit(text)
        self.edit.selectAll()
        buttons = QDialogButtonBox()
        self.ok_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Abbrechen", QDialogButtonBox.ButtonRole.RejectRole)
        self.ok_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.edit.textChanged.connect(lambda value: self.ok_button.setEnabled(bool(value.strip())))
        self.ok_button.setEnabled(bool(text.strip()))
        layout = QVBoxLayout(self)
        layout.addWidget(label_for(self.edit, label))
        layout.addWidget(self.edit)
        layout.addWidget(buttons)
        self.resize(460, 140)
        self.initial_focus_widget = self.edit
        self.edit.setFocus()

    @property
    def value(self) -> str:
        return self.edit.text().strip()


def ask_name(parent: QWidget | None, title: str, label: str, text: str = "") -> str | None:
    """Name oder None bei Abbruch."""
    dialog = NameDialog(title, label, text, parent)
    return dialog.value if dialog.exec() and dialog.value else None
