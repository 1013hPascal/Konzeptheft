"""Gemeinsame Test-Hilfen."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    """Hauptfenster mit eigenen Einstellungen im Testordner. Dialoge werden in den Tests ersetzt."""
    from PySide6.QtCore import QSettings
    from konzeptheft.ui import announcer as announcer_module
    from konzeptheft.core.spelling import MyWords, Spelling
    from konzeptheft.ui import spelling_ui
    from konzeptheft.ui.main_window import MainWindow
    from tests.fake_spelling import FakeChecker
    announcer_module.announcer.reset()
    sounds = []
    monkeypatch.setattr(spelling_ui, "play_error_sound", lambda: sounds.append(1))
    settings = QSettings(str(tmp_path / "einstellungen.ini"), QSettings.Format.IniFormat)
    spelling = Spelling(FakeChecker(), MyWords(tmp_path / "meine-woerter.txt"))
    win = MainWindow(settings, base_folder=tmp_path, spelling=spelling)
    win.sounds = sounds                              # gespielte Töne, für die Tests
    win.show()
    win.initial_focus()
    yield win
    # Selbst schließen statt qtbot.addWidget: qtbot schließt vor diesem Aufräumen, und die
    # Rückfrage "Änderungen speichern?" würde den Test anhalten.
    win.concept.modified = False
    win.close()
    win.deleteLater()
