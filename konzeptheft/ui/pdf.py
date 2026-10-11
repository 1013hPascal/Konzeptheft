"""PDF-Ausgabe mit den Mitteln von Qt (keine zusätzliche Bibliothek).

Liegt in der Oberfläche, weil der Kern nie PySide6 importiert."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from konzeptheft import APP_NAME
from konzeptheft.core.concept import Concept
from konzeptheft.core.export import to_html
from konzeptheft.core.storage import StorageError

PDF_FONT_POINTS = 11


def save_pdf(path: Path, concept: Concept) -> None:
    temp = path.with_name(path.name + ".tmp")
    writer = QPdfWriter(str(temp))
    writer.setTitle(concept.title or path.stem)
    writer.setCreator(APP_NAME)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                     QPageLayout.Orientation.Portrait,
                                     QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter))
    document = QTextDocument()
    font = QFont()
    font.setPointSize(PDF_FONT_POINTS)
    document.setDefaultFont(font)
    document.setHtml(to_html(concept))
    document.print_(writer)
    del writer                                         # schließt die Datei
    try:
        os.replace(temp, path)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise StorageError(f"{path.name} konnte nicht gespeichert werden. Ist die PDF in einem "
                           f"anderen Programm geöffnet?") from exc
