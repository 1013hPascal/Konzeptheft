"""Konzeptheft starten: python main.py [datei.md]

Ohne Datei öffnet das Programm das zuletzt benutzte Konzept, wenn es noch da ist.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from konzeptheft import APP_NAME, __version__
from konzeptheft.ui.main_window import MainWindow


def _german_qt(app: QApplication) -> QTranslator:
    """Deutsche Texte für Qt-eigene Schaltflächen und Dialoge (zum Beispiel "Abbrechen")."""
    translator = QTranslator(app)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale(QLocale.Language.German), "qtbase", "_", folder):
        app.installTranslator(translator)
    return translator


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    _german_qt(app)
    window = MainWindow()
    window.show()
    window.initial_focus()
    files = [Path(a) for a in args if not a.startswith("-")]
    if files:
        window.open_file(files[0])
    else:
        window.open_last_file()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
