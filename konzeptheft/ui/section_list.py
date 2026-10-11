"""Die Abschnittsliste. Sie zeigt immer eine Ebene: die Hauptliste oder eine Unterliste.

Hauptliste: Die ersten beiden Zeilen sind feste Befehle, "Neuer Eintrag" und "Speichern".
Danach folgen die Abschnitte, zum Beispiel "3 Lösung" oder "3.0 Lösung" (mit Unterliste).

Unterliste: nur die Einträge dieser Ebene. Ist sie leer, steht dort eine einzige Zeile
"Kein Eintrag, Alt+N für ersten Untereintrag".

Tasten, die die Liste selbst behandelt:
- Pos1 und Ende springen zum ersten und letzten Abschnitt (nicht zu den Befehlen).
- Pfeil rechts meldet openRequested (Unterliste öffnen), Pfeil links closeRequested (zurück).
- Enter löst itemActivated aus, das Hauptfenster entscheidet, was passiert.
- Menütaste oder Umschalt+F10: Kontextmenü (Qt schickt dafür ein contextMenuEvent).
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QListWidget

from konzeptheft.ui.common import name_widget

NEW_ROW = 0
SAVE_ROW = 1
NEW_TEXT = "Neuer Eintrag, Alt+N"
SAVE_TEXT = "Speichern"
EMPTY_TEXT = "Kein Eintrag, Alt+N für ersten Untereintrag"
MAIN_NAME = "Abschnitte"


class SectionList(QListWidget):
    contextMenuRequested = Signal(QPoint)
    openRequested = Signal()                      # Pfeil rechts
    closeRequested = Signal()                     # Pfeil links

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        name_widget(self, MAIN_NAME)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.is_main = True
        self._entries = 0

    @property
    def first_entry_row(self) -> int:
        return SAVE_ROW + 1 if self.is_main else 0

    def show_level(self, rows: list[str], is_main: bool, name: str,
                   current: int | None) -> None:
        """Eine Ebene eintragen. rows: Text je Eintrag.
        current: Index des Eintrags, der markiert wird; -1 markiert die erste Zeile
        ("Neuer Eintrag" oder "Kein Eintrag"); None behält die Zeile, soweit es sie gibt."""
        row = self.currentRow() if current is None else (
            current + (SAVE_ROW + 1 if is_main else 0) if current >= 0 else 0)
        self.blockSignals(True)
        self.clear()
        self.is_main = is_main
        self._entries = len(rows)
        if is_main:
            self.addItem(NEW_TEXT)
            self.addItem(SAVE_TEXT)
        elif not rows:
            self.addItem(EMPTY_TEXT)
        self.addItems(rows)
        self.blockSignals(False)
        name_widget(self, name)
        self.setCurrentRow(max(0, min(row, self.count() - 1)))

    def section_index(self) -> int | None:
        """Index des markierten Eintrags in seiner Ebene, None auf einer Befehls- oder
        Leer-Zeile."""
        if not self._entries:
            return None
        row = self.currentRow() - self.first_entry_row
        return row if 0 <= row < self._entries else None

    def select_section(self, index: int) -> None:
        self.setCurrentRow(index + self.first_entry_row)

    def section_count(self) -> int:
        return self._entries

    def keyPressEvent(self, event) -> None:
        plain = event.modifiers() in (Qt.KeyboardModifier.NoModifier,
                                      Qt.KeyboardModifier.KeypadModifier)
        key = event.key()
        if plain and key == Qt.Key.Key_Right:
            self.openRequested.emit()
            return
        if plain and key == Qt.Key.Key_Left:
            self.closeRequested.emit()
            return
        if plain and self._entries and key == Qt.Key.Key_Home:
            self.setCurrentRow(self.first_entry_row)
            return
        if plain and key == Qt.Key.Key_End:
            self.setCurrentRow(self.count() - 1)
            return
        super().keyPressEvent(event)

    def _context_menu(self, _pos: QPoint) -> None:
        """Tastatur und Maus: Das Menü gehört immer zum markierten Eintrag."""
        item = self.currentItem()
        if item is None:
            return
        rect = self.visualItemRect(item)
        self.contextMenuRequested.emit(self.viewport().mapToGlobal(rect.bottomLeft()))
