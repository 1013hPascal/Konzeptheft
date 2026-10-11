"""Hintergrund-Aufgaben (übernommen aus dem CodeCockpit). Die Oberfläche blockiert nie.

Fehler gehen nie still verloren: Erwartete Fehler (UpdateError) kommen mit einfachem Text und
Details, unerwartete zusätzlich ins Log.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from PySide6.QtCore import QThread, Signal

from konzeptheft.core.update import Cancelled, UpdateError

log = logging.getLogger(__name__)


class Task(QThread):
    """Führt fn(task) im Hintergrund aus. Ergebnisse kommen über Signale zurück."""
    result = Signal(object)
    error = Signal(str, str)          # einfacher Text, Details
    cancelled = Signal()

    def __init__(self, fn: Callable[["Task"], object], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            outcome = self._fn(self)
        except Cancelled:
            self.cancelled.emit()
        except UpdateError as exc:
            self.error.emit(exc.message, exc.details)
        except Exception as exc:                       # nie den Thread still sterben lassen
            log.exception("Unerwarteter Fehler im Hintergrund")
            self.error.emit("Unerwarteter Fehler.", repr(exc))
        else:
            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.result.emit(outcome)
