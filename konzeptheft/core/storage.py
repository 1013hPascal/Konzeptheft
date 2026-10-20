"""Lesen und Schreiben der Dateien. Geschrieben wird immer erst in eine Hilfsdatei, die dann die
alte Datei ersetzt. So bleibt bei einem Fehler die alte Datei heil.

Gespeichert wird die Projektdatei (.konzept) mit der ganzen Struktur. Daneben mit gleichem Namen
die PDF und die Textdatei für andere Leser. Geöffnet werden .konzept und alte .md-Dateien.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

from konzeptheft.core.concept import Concept
from konzeptheft.core.docx import to_docx_bytes
from konzeptheft.core.export import to_plain_text
from konzeptheft.core.latex import to_latex
from konzeptheft.core.markdown import from_markdown
from konzeptheft.core.project import SUFFIX, ProjectFormatError, from_json, to_json

DATA_FOLDER_NAME = "Dateien"

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent

class StorageError(Exception):
    """Fehler beim Lesen oder Schreiben, mit einer Meldung für den Nutzer."""


def data_folder(base_path: Path = None) -> Path:
    """Der Ordner "Dateien" neben dem Programm. Wird angelegt, wenn er fehlt."""
    base = base_path or base_dir
    folder = base / DATA_FOLDER_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def project_path(path: Path) -> Path:
    """Immer mit der Endung .konzept, auch wenn eine andere eingegeben wurde."""
    if path.suffix.lower() in (SUFFIX, ".md", ".pdf", ".txt"):
        return path.with_suffix(SUFFIX)
    return path.with_name(path.name + SUFFIX)


def text_path(path: Path) -> Path:
    return path.with_suffix(".txt")


def pdf_path(path: Path) -> Path:
    return path.with_suffix(".pdf")


def with_suffix(path: Path, suffix: str) -> Path:
    """Endung anhängen, außer sie ist schon da ("Plan 1.2" wird "Plan 1.2.tex")."""
    return path if path.suffix.lower() == suffix else path.with_name(path.name + suffix)


def latex_path(path: Path) -> Path:
    return with_suffix(path, ".tex")


def docx_path(path: Path) -> Path:
    return with_suffix(path, ".docx")


def write_atomic(path: Path, content: str | bytes) -> None:
    temp = path.with_name(path.name + ".tmp")
    try:
        if isinstance(content, bytes):
            temp.write_bytes(content)
        else:
            temp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temp, path)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise StorageError(f"{path.name} konnte nicht gespeichert werden. {exc.strerror or exc}") \
            from exc


def save_project(path: Path, concept: Concept) -> None:
    write_atomic(path, to_json(concept))


def save_text(path: Path, concept: Concept) -> None:
    write_atomic(path, to_plain_text(concept))


def save_latex(path: Path, concept: Concept) -> None:
    write_atomic(path, to_latex(concept))


def save_docx(path: Path, concept: Concept) -> None:
    write_atomic(path, to_docx_bytes(concept))


def load(path: Path) -> Concept:
    """Öffnet eine .konzept-Datei oder eine alte .md-Datei."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise StorageError(f"{path.name} konnte nicht geöffnet werden. {exc.strerror or exc}") \
            from exc
    try:
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        source = data.decode("cp1252", errors="replace")      # ältere Windows-Dateien
    if path.suffix.lower() == ".md":
        return from_markdown(source, fallback_title=path.stem)
    try:
        return from_json(source, fallback_title=path.stem)
    except ProjectFormatError as exc:
        raise StorageError(f"{path.name} konnte nicht geöffnet werden. {exc}") from exc
