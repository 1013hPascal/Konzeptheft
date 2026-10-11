"""Selbst-Aktualisierung der Exe (übernommen aus dem CodeCockpit, core/update.py).

Quelle ist das neueste Release von 1013hPascal/Konzeptheft auf GitHub. Das CodeCockpit
veröffentlicht dort die ZIP-Datei Konzeptheft.zip mit einem Ordner Konzeptheft-v1.2.0, darin
Konzeptheft.exe, version.txt, README und Lizenz. Eine einzelne Exe am Release geht auch.

- Ein Update gibt es nur, wenn das Release eine höhere Versionsnummer hat als die laufende Exe
  (version.txt neben der Exe, sonst __version__) und eine andere Datei ist.
- Die neue Exe wird heruntergeladen, gegen die Prüfsumme (SHA-256) von GitHub geprüft und wartet
  im Ordner _neu neben der Exe. Nach dem Beenden tauscht ein kleines Skript sie aus. Die bisherige
  Exe kommt vorher in eine Sicherheitskopie.
- Der Ordner Dateien neben der Exe und die Einstellungen bleiben unberührt.

Statt httpx (CodeCockpit) nimmt das Konzeptheft urllib aus Python, ohne neue Bibliothek.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from konzeptheft import APP_NAME, __version__

log = logging.getLogger(__name__)

OWNER, REPO = "1013hPascal", "Konzeptheft"
LATEST_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
ZIP_PREFIX = "konzeptheft"                 # nur Konzeptheft.zip, keine fremde ZIP-Datei
PENDING = "_neu"
VERSION_FILE = "version.txt"
BACKUP_FOLDER = "Sicherheitskopien"
NO_CONNECTION = "Keine Verbindung zu GitHub. Bitte später erneut versuchen."
TIMEOUT = 20
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class UpdateError(Exception):
    """Fehler mit einfachem Text für den Nutzer und Details für das Log."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class Cancelled(Exception):
    """Der Nutzer hat abgebrochen."""


@dataclass
class Update:
    tag: str
    notes: str
    asset_name: str
    url: str                              # Download-Adresse der Datei
    size: int
    digest: str                           # SHA-256, klein geschrieben

    @property
    def version(self) -> str:
        return self.tag.lstrip("v")

    @property
    def is_zip(self) -> bool:
        return self.asset_name.lower().endswith(".zip")

    @property
    def size_text(self) -> str:
        return f"{max(1, round(self.size / (1024 * 1024)))} MB"


# -- Netz ---------------------------------------------------------------------------------------
def _request(url: str, accept: str = "application/vnd.github+json"):
    request = urllib.request.Request(url, headers={"Accept": accept,
                                                   "User-Agent": f"{APP_NAME}/{__version__}"})
    return urllib.request.urlopen(request, timeout=TIMEOUT)


def fetch_json(url: str) -> dict | None:
    """JSON von GitHub, None bei 404 (noch kein Release)."""
    try:
        with _request(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise UpdateError("GitHub hat die Anfrage nach Updates abgelehnt. Bitte später erneut "
                          "versuchen.", f"HTTP {exc.code}") from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise UpdateError(NO_CONNECTION, repr(exc)) from None


def fetch_file(url: str, target: Path, cancel: threading.Event | None = None) -> str:
    """Datei laden, gibt ihre SHA-256 zurück."""
    digest = hashlib.sha256()
    try:
        with _request(url, "application/octet-stream") as response, open(target, "wb") as file:
            while chunk := response.read(256 * 1024):
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                digest.update(chunk)
                file.write(chunk)
    except urllib.error.HTTPError as exc:
        raise UpdateError("Die neue Version ließ sich nicht herunterladen.",
                          f"HTTP {exc.code}") from None
    except (urllib.error.URLError, OSError) as exc:
        raise UpdateError(NO_CONNECTION, repr(exc)) from None
    return digest.hexdigest()


# -- Prüfen -------------------------------------------------------------------------------------
def own_exe() -> Path | None:
    """Die laufende Exe, None beim Start aus dem Code."""
    return Path(sys.executable) if getattr(sys, "frozen", False) else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", text.strip())
    return tuple(int(x) for x in match.groups()) if match else None


def own_version(exe_path: Path | None) -> tuple[int, int, int] | None:
    """Die höhere aus version.txt neben der Exe und __version__."""
    found = [v for v in (parse_version(__version__),) if v]
    if exe_path is not None:
        try:
            found += [v for v in (parse_version((exe_path.parent / VERSION_FILE).read_text(
                encoding="utf-8")),) if v]
        except OSError:
            pass
    return max(found) if found else None


def from_release(data: dict) -> Update | None:
    """Exe-Datei bevorzugt, sonst Konzeptheft.zip. Nur Dateien mit Prüfsumme."""
    usable = [a for a in data.get("assets") or []
              if (a.get("digest") or "").startswith("sha256:")]
    exes = [a for a in usable if a.get("name", "").lower().endswith(".exe")]
    zips = [a for a in usable if a.get("name", "").lower().endswith(".zip")
            and a.get("name", "").lower().startswith(ZIP_PREFIX)]
    for asset in exes + zips:
        return Update(data.get("tag_name", ""), data.get("body") or "", asset["name"],
                      asset["browser_download_url"], int(asset.get("size", 0)),
                      asset["digest"].split(":", 1)[1].lower())
    return None


def is_newer(update: Update, exe_path: Path) -> bool:
    if sha256(exe_path) == update.digest:
        return False
    mine, theirs = own_version(exe_path), parse_version(update.tag)
    return mine is not None and theirs is not None and theirs > mine


def check(exe_path: Path, skipped: str = "",
          fetch: Callable[[str], dict | None] = fetch_json) -> Update | None:
    """Gibt es ein Update? skipped: vom Nutzer übersprungene Version (Tag)."""
    data = fetch(LATEST_URL)
    update = from_release(data) if data else None
    if update is None or (skipped and update.tag == skipped):
        return None
    return update if is_newer(update, exe_path) else None


# -- Laden --------------------------------------------------------------------------------------
def _beside(name: str) -> bool:
    """Was aus der ZIP-Datei neben die Exe kommt: README, Lizenz und version.txt."""
    lower = Path(name).name.lower()
    return (lower.startswith("readme") or lower.split(".")[0] in ("license", "licence", "copying")
            or lower == VERSION_FILE)


def download(update: Update, exe_path: Path, cancel: threading.Event | None = None,
             fetch: Callable[[str, Path, threading.Event | None], str] = fetch_file) -> Path:
    """Neue Exe nach _neu laden, unter dem Namen der laufenden Exe. Prüft die Prüfsumme."""
    pending = exe_path.parent / PENDING
    shutil.rmtree(pending, ignore_errors=True)
    pending.mkdir()
    target = pending / (update.asset_name if update.is_zip else exe_path.name)
    try:
        digest = fetch(update.url, target, cancel)
        if digest != update.digest:
            raise UpdateError("Die heruntergeladene Datei ist beschädigt oder verändert. Sie "
                              "wurde gelöscht, die bisherige Version bleibt.", "SHA-256 weicht ab")
        if update.is_zip:
            return _exe_from_zip(target, pending / exe_path.name)
        return target
    except BaseException:
        shutil.rmtree(pending, ignore_errors=True)
        raise


def _exe_from_zip(archive: Path, target: Path) -> Path:
    """Die Exe aus der geprüften ZIP-Datei holen, unter dem Namen der laufenden Exe. Nur diese
    Datei und README, Lizenz, version.txt aus demselben Ordner werden geschrieben, an einen festen
    Ort, egal welche Pfade in der ZIP stehen."""
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = [m for m in bundle.infolist()
                       if not m.is_dir() and m.filename.lower().endswith(".exe")]
            same = [m for m in members if Path(m.filename).name.lower() == target.name.lower()]
            chosen = (same or members)[:1]
            if not chosen or len(members) > 1 and not same:
                raise UpdateError("In der ZIP-Datei der neuen Version steckt keine passende Exe. "
                                  "Die bisherige Version bleibt.",
                                  ", ".join(m.filename for m in members) or "keine Exe")
            if any("_internal/" in m.filename.replace("\\", "/") for m in bundle.infolist()):
                raise UpdateError("Die neue Version ist ein Programmordner. Den kann das "
                                  "Konzeptheft nicht selbst austauschen. Laden Sie die ZIP-Datei "
                                  "bitte von der Release-Seite.", archive.name)
            with bundle.open(chosen[0]) as source, open(target, "wb") as file:
                shutil.copyfileobj(source, file)
            folder = Path(chosen[0].filename.replace("\\", "/")).parent
            for member in bundle.infolist():
                path = Path(member.filename.replace("\\", "/"))
                if member.is_dir() or path.parent != folder or not _beside(path.name):
                    continue
                with bundle.open(member) as source, open(target.parent / path.name, "wb") as file:
                    shutil.copyfileobj(source, file)
    except zipfile.BadZipFile as exc:
        raise UpdateError("Die ZIP-Datei der neuen Version ist beschädigt. Die bisherige Version "
                          "bleibt.", repr(exc)) from None
    archive.unlink()
    return target


def is_waiting(exe_path: Path) -> bool:
    return (exe_path.parent / PENDING / exe_path.name).is_file()


# -- Austauschen --------------------------------------------------------------------------------
def backup_folder(version: str) -> Path:
    """Ordner für die bisherige Exe, unter %LOCALAPPDATA%\\Konzeptheft\\Sicherheitskopien."""
    base = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / APP_NAME
    folder = base / BACKUP_FOLDER / f"{datetime.now():%Y-%m-%d_%H-%M-%S} vor Version {version}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def swap_script(exe_path: Path, version: str, start: bool, pid: int | None = None) -> Path:
    """Skript, das auf das Ende des Programms wartet, die bisherige Exe (und README, Lizenz,
    version.txt) in die Sicherheitskopie verschiebt, die neuen aus _neu holt und, wenn gewünscht,
    das Programm wieder startet. Muster aus dem CodeCockpit (exe.swap_script)."""
    exe_dir = exe_path.parent
    pending = exe_dir / PENDING
    new = pending / exe_path.name
    if not new.is_file():
        raise UpdateError("Es wartet keine neue Version.")
    backup = backup_folder(version)
    docs = sorted(p for p in pending.iterdir() if p.is_file() and _beside(p.name))
    old_items = [exe_path] + [exe_dir / d.name for d in docs if (exe_dir / d.name).is_file()]
    new_items = [new] + docs
    pid = pid or os.getpid()
    system = r"%SystemRoot%\System32"
    lines = ["@echo off", "chcp 65001 >nul", "set versuche=0", ":warten",
             f'"{system}\\tasklist.exe" /FI "PID eq {pid}" /NH | "{system}\\find.exe" " {pid} " >nul',
             "if not errorlevel 1 (timeout /t 1 /nobreak >nul & goto warten)"]
    moves = [(item, backup / item.name) for item in old_items] + \
            [(item, exe_dir / item.name) for item in new_items]
    for number, (source, target) in enumerate(moves, start=1):
        lines += [f":schieben{number}",
                  f'move /Y "{source}" "{target}" >nul 2>nul',
                  f"if not errorlevel 1 goto fertig{number}",
                  "set /a versuche+=1",
                  "if %versuche% geq 30 goto aufgeben",
                  "timeout /t 1 /nobreak >nul",
                  f"goto schieben{number}",
                  f":fertig{number}"]
    lines.append(f'rmdir /S /Q "{pending}"')
    if start:
        lines.append(f'start "" "{exe_path}"')
    lines.append('(goto) 2>nul & del "%~f0"')
    lines.append(":aufgeben")
    # Klappt das Tauschen nicht, kommt schon Verschobenes zurück; die neue Exe wartet weiter
    for item in old_items:
        lines.append(f'if exist "{backup / item.name}" if not exist "{item}" '
                     f'move /Y "{backup / item.name}" "{item}" >nul 2>nul')
    if start:
        lines.append(f'if exist "{exe_path}" start "" "{exe_path}"')
    lines.append('(goto) 2>nul & del "%~f0"')
    script = Path(tempfile.gettempdir()) / "konzeptheft-neustart.bat"
    script.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    return script


def launch(script: Path) -> None:
    """Skript unsichtbar starten. Es läuft weiter, wenn das Programm sich beendet."""
    subprocess.Popen(["cmd.exe", "/c", str(script)], close_fds=True,
                     creationflags=FLAGS | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
