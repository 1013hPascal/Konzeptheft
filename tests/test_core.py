"""Kern: Datenmodell mit Unterlisten, Projektdatei, alte Markdown-Dateien, Ausgabe."""
from __future__ import annotations

import pytest

from konzeptheft.core import storage
from konzeptheft.core.concept import (Concept, Section, export_number, heading_level,
                                      number_text, set_heading)
from konzeptheft.core.export import to_html, to_plain_text
from konzeptheft.core.markdown import UNNAMED_SECTION, from_markdown
from konzeptheft.core.project import ProjectFormatError, from_json, to_json


def sample() -> Concept:
    teil = Section("Teil", "Text vom Teil", [Section("Detail", "# Kern\nganz tief")])
    return Concept("Mein Plan", [Section("Einleitung", "Hallo"), Section("Problem"),
                                 Section("Lösung", "# Idee\nText\n\n## Detail\nmehr",
                                         [teil, Section("Zweiter Teil")])])


# -- Nummern ------------------------------------------------------------------------------
def test_number_text():
    assert number_text([3], 0) == "3"
    assert number_text([3], 1) == "3.0"
    assert number_text([3], 3) == "3.0.0.0"
    assert number_text([3, 1], 0) == "3.1"
    assert number_text([3, 1], 2) == "3.1.0.0"
    assert export_number([3]) == "3."
    assert export_number([3, 1, 2]) == "3.1.2"


def test_labels_show_sublists():
    concept = sample()
    loesung = concept.sections[2]
    teil = loesung.children[0]
    assert concept.label(concept.sections[0]) == "1 Einleitung"
    assert concept.label(loesung) == "3.0.0 Lösung"            # zwei Unterebenen darunter
    assert concept.label(teil) == "3.1.0 Teil"
    assert concept.label(loesung.children[1]) == "3.2 Zweiter Teil"
    assert concept.label(teil.children[0]) == "3.1.1 Detail"


def test_one_zero_per_sublevel():
    four = Section("D")
    for name in "CBA":
        four = Section(name, children=[four])
    concept = Concept("", [four])
    a = concept.sections[0]
    assert concept.label(a) == "1.0.0.0 A"
    assert concept.label(a.children[0]) == "1.1.0.0 B"
    assert concept.label(a.children[0].children[0]) == "1.1.1.0 C"
    assert concept.label(a.children[0].children[0].children[0]) == "1.1.1.1 D"


def test_walk_and_parents():
    concept = sample()
    numbers = [n for n, _s in concept.walk()]
    assert numbers == [[1], [2], [3], [3, 1], [3, 1, 1], [3, 2]]
    detail = concept.sections[2].children[0].children[0]
    assert concept.parent_of(detail) is concept.sections[2].children[0]
    assert concept.parent_of(concept.sections[0]) is None


# -- Ändern -------------------------------------------------------------------------------
def test_insert_after_renumbers():
    concept = Concept("", [Section(n) for n in "ABCDE"])
    index = concept.insert_after(3, "Neu")
    assert index == 4
    assert [s.name for s in concept.sections] == ["A", "B", "C", "D", "Neu", "E"]
    assert concept.label(concept.sections[5]) == "6 E"
    assert concept.modified


def test_sub_entries_and_renumbering():
    concept = Concept("", [Section("A"), Section("B")])
    b = concept.sections[1]
    assert concept.insert_after(-1, "Erstes", b) == 0
    assert concept.insert_after(0, "Zweites", b) == 1
    assert concept.insert_after(0, "Dazwischen", b) == 1
    assert [s.name for s in b.children] == ["Erstes", "Dazwischen", "Zweites"]
    assert concept.label(b.children[2]) == "2.3 Zweites"
    assert concept.label(b) == "2.0 B"


def test_move_within_level():
    concept = sample()
    loesung = concept.sections[2]
    assert concept.move(1, -1, loesung) == 0
    assert [s.name for s in loesung.children] == ["Zweiter Teil", "Teil"]
    assert concept.move(0, -1, loesung) is None


def test_remove_with_children():
    concept = sample()
    teil = concept.sections[2].children[0]
    assert concept.sections[2].count_all() == 3
    removed = concept.remove(2)
    assert removed.name == "Lösung"
    assert not concept.contains(teil)


def test_sections_compare_by_identity():
    a, b = Section("Gleich"), Section("Gleich")
    concept = Concept("", [a, b])
    assert concept.numbers_of(b) == [2]


def test_heading_helpers():
    assert set_heading("Text", 1) == "# Text"
    assert set_heading("## Text", 3) == "### Text"
    assert set_heading("# Text", 0) == "Text"
    assert heading_level("#hashtag") == 0


# -- Projektdatei -------------------------------------------------------------------------
def test_project_round_trip():
    concept = sample()
    loaded = from_json(to_json(concept))
    assert loaded.title == "Mein Plan"
    assert [(n, s.name, s.text) for n, s in loaded.walk()] == \
        [(n, s.name, s.text) for n, s in concept.walk()]
    assert not loaded.modified


def test_project_is_readable_json():
    text = to_json(sample())
    assert '"format": "konzeptheft"' in text
    assert "Lösung" in text                         # Umlaute bleiben lesbar


@pytest.mark.parametrize("source", ["kein json", '{"format": "anders"}',
                                    '{"format": "konzeptheft", "version": 99}',
                                    '{"format": "konzeptheft", "version": 1, "sections": [{}]}'])
def test_project_rejects_bad_files(source):
    with pytest.raises(ProjectFormatError):
        from_json(source)


def test_project_rejects_too_deep():
    deep = Section("5", children=[Section("zu tief")])
    for name in "4321":
        deep = Section(name, children=[deep])
    with pytest.raises(ProjectFormatError, match="vier"):
        from_json(to_json(Concept("T", [deep])))


# -- Alte Markdown-Dateien ----------------------------------------------------------------
def test_old_markdown_still_opens():
    loaded = from_markdown("# T\n\n## A\n\n### Idee\nx\n\n## B\n", fallback_title="datei")
    assert loaded.title == "T"
    assert [s.name for s in loaded.sections] == ["A", "B"]
    assert loaded.sections[0].text == "# Idee\nx"


def test_foreign_markdown_keeps_text_before_sections():
    loaded = from_markdown("Vorrede\n\n## Erster\nInhalt\n", fallback_title="datei")
    assert loaded.title == "datei"
    assert [s.name for s in loaded.sections] == [UNNAMED_SECTION, "Erster"]


# -- Ausgabe ------------------------------------------------------------------------------
def test_plain_text_has_numbers_and_no_markdown():
    text = to_plain_text(sample())
    lines = text.splitlines()
    assert lines[0] == "Mein Plan"
    for heading in ("1. Einleitung", "3. Lösung", "3.1 Teil", "3.1.1 Detail", "3.2 Zweiter Teil"):
        assert heading in lines
    assert "#" not in text
    assert ".0" not in text


def test_html_heading_levels_follow_depth():
    html = to_html(sample())
    assert "<h1>3. Lösung</h1>" in html
    assert "<h2>3.1 Teil</h2>" in html
    assert "<h3>3.1.1 Detail</h3>" in html
    assert "<h2>Idee</h2>" in html                  # Ebene 1 im Text von Abschnitt 3
    assert "<h3>Detail</h3>" in html                # Ebene 2 im Text von Abschnitt 3
    assert "<h4>Kern</h4>" in html                  # Ebene 1 im Text von 3.1.1
    assert "<h1>Mein Plan" not in html              # Titel ist keine Überschrift


def test_html_escapes_text():
    html = to_html(Concept("A & B", [Section("<x>", "1 < 2")]))
    assert "A &amp; B" in html and "&lt;x&gt;" in html and "1 &lt; 2" in html


# -- Dateien ------------------------------------------------------------------------------
def test_storage_round_trip(tmp_path):
    path = storage.project_path(tmp_path / "plan")
    assert path.name == "plan.konzept"
    storage.save_project(path, sample())
    storage.save_text(storage.text_path(path), sample())
    loaded = storage.load(path)
    assert loaded.sections[2].children[0].children[0].text == "# Kern\nganz tief"
    assert storage.text_path(path).read_text(encoding="utf-8").startswith("Mein Plan")
    assert not list(tmp_path.glob("*.tmp"))


def test_project_path_replaces_other_suffixes(tmp_path):
    assert storage.project_path(tmp_path / "a.md").name == "a.konzept"
    assert storage.project_path(tmp_path / "a.b").name == "a.b.konzept"


def test_data_folder_is_created(tmp_path):
    folder = storage.data_folder(tmp_path)
    assert folder == tmp_path / "Dateien" and folder.is_dir()


def test_storage_reads_old_windows_encoding(tmp_path):
    path = tmp_path / "alt.md"
    path.write_bytes("# Übung\n\n## Größe\n".encode("cp1252"))
    loaded = storage.load(path)
    assert loaded.title == "Übung"
    assert loaded.sections[0].name == "Größe"


def test_storage_error_messages(tmp_path):
    with pytest.raises(storage.StorageError, match="fehlt.konzept"):
        storage.load(tmp_path / "fehlt.konzept")
    bad = tmp_path / "kaputt.konzept"
    bad.write_text("kein json", encoding="utf-8")
    with pytest.raises(storage.StorageError, match="keine Konzeptheft-Datei"):
        storage.load(bad)
