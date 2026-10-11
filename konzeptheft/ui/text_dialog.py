"""Fenster, das einen Text als Liste zeigt: eine Zeile pro Eintrag (übernommen aus dem CodeCockpit).

Eine Liste lässt sich mit NVDA und Braillezeile zuverlässiger lesen als ein schreibgeschütztes
Textfeld. Pfeiltasten lesen Zeile für Zeile, Tab führt zu "Schließen", Escape schließt.
"""
from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QPushButton, QVBoxLayout, QWidget

from konzeptheft.ui.common import FocusDialog, name_widget


class TextDialog(FocusDialog):
    def __init__(self, title: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.lines = [line.strip() for line in text.splitlines() if line.strip()]
        self.list = QListWidget()
        name_widget(self.list, title)
        self.list.addItems(self.lines)
        self.list.setCurrentRow(0)
        self.list.setWordWrap(True)
        self.close_button = QPushButton("&Schließen")
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(self.close_button)
        self.resize(640, 520)
        self.list.setFocus()
        self.initial_focus_widget = self.list
