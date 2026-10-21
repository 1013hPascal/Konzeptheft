"""Konzeptheft starten: python main.py [datei.konzept]

Ohne Datei startet das Programm mit einem leeren Konzept (Wunsch vom 21.10.2026).

Optionen:
  --selbsttest  kurz starten und mit Code 0 beenden, ohne Datei und ohne Update-Suche
                (für den Test der Exe im CodeCockpit)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTimer, QTranslator
from PySide6.QtWidgets import QApplication

from konzeptheft import APP_NAME, __version__
from konzeptheft.ui.main_window import MainWindow

SELF_TEST_MS = 1500


def _german_qt(app: QApplication) -> QTranslator:
    """Deutsche Texte für Qt-eigene Schaltflächen und Dialoge (zum Beispiel "Abbrechen")."""
    translator = QTranslator(app)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale(QLocale.Language.German), "qtbase", "_", folder):
        app.installTranslator(translator)
    return translator


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    self_test = "--selbsttest" in args
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    _german_qt(app)
    if self_test:
        # Eigene Einstellungen im Speicher: Der Test berührt nie die echten Daten
        import tempfile
        settings = QSettings(str(Path(tempfile.mkdtemp(prefix="konzeptheft-selbsttest-"))
                                 / "einstellungen.ini"), QSettings.Format.IniFormat)
        window = MainWindow(settings, exe_path=None)
        window.show()
        QTimer.singleShot(SELF_TEST_MS, lambda: app.exit(0))
        return app.exec()
    window = MainWindow()
    window.show()
    window.initial_focus()
    files = [Path(a) for a in args if not a.startswith("-")]
    if files:
        window.open_file(files[0])
    window.updater.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
