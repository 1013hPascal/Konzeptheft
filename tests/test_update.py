"""Selbst-Aktualisierung: Release lesen, Version vergleichen, laden, prüfen, Austausch-Skript."""
from __future__ import annotations

import hashlib
import zipfile

import pytest

from konzeptheft.core import update
from konzeptheft.ui import update_ui


def release(assets, tag="v9.0.0", notes="Neu"):
    return {"tag_name": tag, "body": notes, "assets": assets}


def asset(name, digest="sha256:" + "a" * 64, size=3_000_000):
    return {"name": name, "digest": digest, "size": size,
            "browser_download_url": f"https://example.invalid/{name}"}


@pytest.fixture
def exe(tmp_path):
    folder = tmp_path / "Konzeptheft-v0.1.0"
    folder.mkdir()
    path = folder / "Konzeptheft.exe"
    path.write_bytes(b"alte exe")
    (folder / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    return path


def test_from_release_prefers_exe_then_zip():
    found = update.from_release(release([asset("Konzeptheft.zip"), asset("Konzeptheft.exe")]))
    assert found.asset_name == "Konzeptheft.exe"
    found = update.from_release(release([asset("Konzeptheft.zip"), asset("Fremd.zip")]))
    assert found.asset_name == "Konzeptheft.zip" and found.is_zip
    assert found.version == "9.0.0" and found.size_text == "3 MB"


def test_from_release_needs_digest_and_own_zip():
    assert update.from_release(release([asset("Konzeptheft.exe", digest="")])) is None
    assert update.from_release(release([asset("Anderes.zip")])) is None


def test_own_version_uses_version_file(exe):
    (exe.parent / "version.txt").write_text("2.3.4\n", encoding="utf-8")
    assert update.own_version(exe) == (2, 3, 4)


def test_check_only_offers_higher_version(exe):
    data = release([asset("Konzeptheft.zip")], tag="v0.2.0")
    assert update.check(exe, fetch=lambda url: data).tag == "v0.2.0"
    assert update.check(exe, skipped="v0.2.0", fetch=lambda url: data) is None
    old = release([asset("Konzeptheft.zip")], tag="v0.1.0")
    assert update.check(exe, fetch=lambda url: old) is None
    assert update.check(exe, fetch=lambda url: None) is None          # noch kein Release
    assert url_seen(exe) == update.LATEST_URL


def url_seen(exe):
    seen = []
    update.check(exe, fetch=lambda url: seen.append(url))
    return seen[0]


def test_same_file_is_never_an_update(exe):
    digest = "sha256:" + hashlib.sha256(b"alte exe").hexdigest()
    data = release([asset("Konzeptheft.exe", digest=digest)], tag="v5.0.0")
    assert update.check(exe, fetch=lambda url: data) is None


def make_zip(tmp_path, exe_bytes=b"neue exe", extra=()):
    archive = tmp_path / "quelle.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("Konzeptheft-v0.2.0/Konzeptheft.exe", exe_bytes)
        bundle.writestr("Konzeptheft-v0.2.0/version.txt", "0.2.0\n")
        bundle.writestr("Konzeptheft-v0.2.0/README.md", "neu")
        bundle.writestr("Konzeptheft-v0.2.0/Dateien/fremd.konzept", "nicht anfassen")
        for name, data in extra:
            bundle.writestr(name, data)
    return archive


def fake_download(source):
    def fetch(url, target, cancel=None):
        target.write_bytes(source.read_bytes())
        return hashlib.sha256(source.read_bytes()).hexdigest()
    return fetch


def test_download_zip_checks_digest_and_unpacks(exe, tmp_path):
    archive = make_zip(tmp_path)
    found = update.Update("v0.2.0", "", "Konzeptheft.zip", "u", 1,
                          hashlib.sha256(archive.read_bytes()).hexdigest())
    new = update.download(found, exe, fetch=fake_download(archive))
    assert new == exe.parent / "_neu" / "Konzeptheft.exe"
    assert new.read_bytes() == b"neue exe"
    names = sorted(p.name for p in new.parent.iterdir())
    assert names == ["Konzeptheft.exe", "README.md", "version.txt"]     # keine Dateien-Ordner
    assert update.is_waiting(exe)


def test_download_with_wrong_digest_is_removed(exe, tmp_path):
    archive = make_zip(tmp_path)
    found = update.Update("v0.2.0", "", "Konzeptheft.zip", "u", 1, "0" * 64)
    with pytest.raises(update.UpdateError, match="beschädigt"):
        update.download(found, exe, fetch=fake_download(archive))
    assert not (exe.parent / "_neu").exists()
    assert exe.read_bytes() == b"alte exe"


def test_program_folder_is_refused(exe, tmp_path):
    archive = make_zip(tmp_path, extra=[("Konzeptheft-v0.2.0/_internal/x.dll", "x")])
    found = update.Update("v0.2.0", "", "Konzeptheft.zip", "u", 1,
                          hashlib.sha256(archive.read_bytes()).hexdigest())
    with pytest.raises(update.UpdateError, match="Programmordner"):
        update.download(found, exe, fetch=fake_download(archive))


def test_swap_script(exe, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    archive = make_zip(tmp_path)
    found = update.Update("v0.2.0", "", "Konzeptheft.zip", "u", 1,
                          hashlib.sha256(archive.read_bytes()).hexdigest())
    update.download(found, exe, fetch=fake_download(archive))
    script = update.swap_script(exe, "0.2.0", start=True, pid=4242)
    text = script.read_bytes().decode("utf-8")
    assert "PID eq 4242" in text
    assert f'move /Y "{exe}"' in text
    assert f'move /Y "{exe.parent / "_neu" / "Konzeptheft.exe"}" "{exe}"' in text
    assert f'start "" "{exe}"' in text
    assert "\r\n" in text
    backups = list((tmp_path / "appdata" / "Konzeptheft" / "Sicherheitskopien").iterdir())
    assert len(backups) == 1 and "0.2.0" in backups[0].name


def test_swap_without_waiting_update(exe):
    with pytest.raises(update.UpdateError):
        update.swap_script(exe, "0.2.0", start=False)


# -- Oberfläche -------------------------------------------------------------------------------
def test_check_now_from_code_explains(window, monkeypatch):
    shown = []
    monkeypatch.setattr(update_ui, "show_info", lambda parent, title, text: shown.append(text))
    window.updater.check_now()
    assert "nur für die Exe" in shown[0]


def test_found_none_manual_says_current(window, monkeypatch):
    shown = []
    monkeypatch.setattr(update_ui, "show_info", lambda parent, title, text: shown.append(text))
    window.updater.found(None, manual=True)
    assert shown == ["Konzeptheft ist aktuell."]


def test_skip_is_remembered(window, monkeypatch):
    monkeypatch.setattr(update_ui, "ask_update", lambda parent, found: update_ui.SKIP)
    found = update.Update("v0.2.0", "", "Konzeptheft.zip", "u", 1, "0" * 64)
    window.updater.ask(found)
    assert window.settings.value(update_ui.SKIPPED_KEY) == "v0.2.0"


def test_check_at_start_setting(window):
    assert window.updater.check_at_start
    window.act_update_start.setChecked(False)
    assert not window.updater.check_at_start
