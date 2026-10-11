"""Updates der Exe: Prüfung beim Start, Rückfrage, Austausch (übernommen aus dem CodeCockpit).

Die Prüfung läuft einmal bei jedem Start still im Hintergrund, nur in der Exe. Nur wenn es eine
neue Version gibt, kommt eine Rückfrage. Fehler der automatischen Prüfung landen nur im Log.
Hilfe, Nach Updates suchen prüft sofort und meldet auch „aktuell“ und Fehler.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from konzeptheft import APP_NAME
from konzeptheft.core import update
from konzeptheft.ui.announcer import announce
from konzeptheft.ui.common import ask_buttons, show_error, show_info
from konzeptheft.ui.tasks import Task

if TYPE_CHECKING:
    from konzeptheft.ui.main_window import MainWindow

log = logging.getLogger(__name__)

FIRST_CHECK_MS = 10_000                  # nach dem Start, damit das Fenster erst in Ruhe aufbaut
RETRY_MS = 60_000                        # Rückfrage verschieben, solange ein Dialog offen ist
TITLE = "Update"
CHECK_KEY = "update/check_at_start"
SKIPPED_KEY = "update/skipped"

UPDATE, NOTES, SKIP, LATER = "update", "notes", "skip", "later"


class Updater(QObject):
    def __init__(self, window: "MainWindow", exe_path: Path | None = None) -> None:
        super().__init__(window)
        self.window = window
        self.settings = window.settings
        self.task: Task | None = None
        self.waiting: update.Update | None = None     # heruntergeladen, Austausch beim Beenden
        self.restart_requested = False
        self.exe_path = exe_path if exe_path is not None else update.own_exe()

    @property
    def check_at_start(self) -> bool:
        return str(self.settings.value(CHECK_KEY, "true")).lower() == "true"

    @check_at_start.setter
    def check_at_start(self, value: bool) -> None:
        self.settings.setValue(CHECK_KEY, "true" if value else "false")

    def start(self) -> None:
        """Nur in der Exe."""
        if self.exe_path is not None and self.check_at_start:
            QTimer.singleShot(FIRST_CHECK_MS, lambda: self.run(manual=False))

    # -- Prüfen -----------------------------------------------------------------------------
    def check_now(self) -> None:
        """Hilfe, Nach Updates suchen."""
        if self.exe_path is None:
            show_info(self.window, TITLE, "Updates gibt es nur für die Exe. Sie haben das "
                      "Konzeptheft aus dem Code gestartet. Neuerungen holen Sie dort mit Git.")
            return
        if self.waiting is not None:
            self.offer_restart(self.waiting)
            return
        announce("Suche nach Updates.")
        self.run(manual=True)

    def run(self, manual: bool) -> None:
        if self.task is not None or self.waiting is not None:
            return
        skipped = "" if manual else str(self.settings.value(SKIPPED_KEY, ""))
        exe_path = self.exe_path
        self._start_task(lambda task: update.check(exe_path, skipped),
                         lambda found: self.found(found, manual),
                         "Nach Updates suchen" if manual else None)

    def _start_task(self, work, done, failed_title: str | None) -> None:
        task = Task(work, self)
        self.task = task

        def finished() -> None:
            self.task = None

        def failed(message: str, details: str) -> None:
            log.warning("Update: %s %s", message, details)
            if failed_title is not None:
                show_error(self.window, failed_title, message)

        task.result.connect(done)
        task.error.connect(failed)
        task.finished.connect(finished)
        task.start()

    def found(self, found: update.Update | None, manual: bool) -> None:
        if found is None:
            if manual:
                show_info(self.window, TITLE, f"{APP_NAME} ist aktuell.")
            return
        if not manual and QApplication.activeModalWidget() is not None:
            QTimer.singleShot(RETRY_MS, lambda: self.found(found, manual))
            return
        self.ask(found)

    # -- Rückfrage --------------------------------------------------------------------------
    def ask(self, found: update.Update) -> None:
        while True:
            answer = ask_update(self.window, found)
            if answer != NOTES:
                break
            from konzeptheft.ui.text_dialog import TextDialog
            TextDialog(f"Versionshinweise {found.version}", found.notes, parent=self.window).exec()
        if answer == SKIP:
            self.settings.setValue(SKIPPED_KEY, found.tag)
            announce(f"Version {found.version} wird übersprungen.")
        elif answer == UPDATE:
            self.download(found)

    def download(self, found: update.Update) -> None:
        exe_path = self.exe_path
        announce("Update wird heruntergeladen.")
        self._start_task(lambda task: update.download(found, exe_path, task.cancel_event),
                         lambda _path: self.downloaded(found), "Update herunterladen")

    def downloaded(self, found: update.Update) -> None:
        self.waiting = found
        self.offer_restart(found)

    def offer_restart(self, found: update.Update) -> None:
        choice = ask_buttons(self.window, TITLE, f"Version {found.version} ist heruntergeladen "
                             f"und geprüft. Zum Übernehmen startet {APP_NAME} neu. Jetzt neu "
                             "starten?", ["Neu starten", "Später"], default=1, escape=1)
        if choice != 0:
            announce("Das Update wird beim Beenden übernommen.")
            return
        self.restart_requested = True
        self.window.close()                       # fragt bei Änderungen nach dem Speichern

    # -- Austausch --------------------------------------------------------------------------
    def shutdown(self) -> None:
        """Beim Beenden: laufende Prüfung abbrechen, wartendes Update übernehmen."""
        if self.task is not None:
            self.task.cancel()
            self.task.wait(5000)
        if self.waiting is None or self.exe_path is None or not update.is_waiting(self.exe_path):
            return
        start = self.restart_requested
        try:
            script = update.swap_script(self.exe_path, self.waiting.version, start)
        except (update.UpdateError, OSError) as exc:
            log.warning("Update-Austausch: %s", exc)
            return
        self.waiting = None
        update.launch(script)


def ask_update(parent, found: update.Update) -> str:
    """Rückfrage mit Aktualisieren, Versionshinweise, Überspringen und Später (Vorgabe)."""
    box = QMessageBox(QMessageBox.Icon.Question, "Update verfügbar",
                      f"Version {found.version} von {APP_NAME} ist verfügbar ({found.size_text}). "
                      "Ihre Konzepte im Ordner Dateien und die Einstellungen bleiben erhalten. "
                      "Die bisherige Exe kommt in die Sicherheitskopien. Jetzt aktualisieren?",
                      QMessageBox.StandardButton.NoButton, parent)
    buttons = {box.addButton("&Aktualisieren", QMessageBox.ButtonRole.AcceptRole): UPDATE}
    if found.notes.strip():
        buttons[box.addButton("&Versionshinweise", QMessageBox.ButtonRole.ActionRole)] = NOTES
    buttons[box.addButton("Diese Version ü&berspringen", QMessageBox.ButtonRole.DestructiveRole)] \
        = SKIP
    later = box.addButton("&Später", QMessageBox.ButtonRole.RejectRole)
    buttons[later] = LATER
    box.setDefaultButton(later)
    box.setEscapeButton(later)
    box.exec()
    return buttons.get(box.clickedButton(), LATER)
