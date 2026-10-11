"""Oberfläche: Liste, Textfeld, Tasten, Speichern und Öffnen."""
from __future__ import annotations

from PySide6.QtCore import Qt

from konzeptheft.core.concept import Concept, Section
from konzeptheft.ui import main_window as mw
from konzeptheft.ui.announcer import announcer
from konzeptheft.ui.section_list import EMPTY_TEXT, NEW_ROW, SAVE_ROW

FIRST_SECTION_ROW = 2


def names(window) -> list[str]:
    return [s.name for s in window.concept.sections]


def fill(window, *section_names: str) -> None:
    window.set_concept(Concept("Test", [Section(n) for n in section_names]), None)


def answer_name(monkeypatch, value):
    monkeypatch.setattr(mw, "ask_name", lambda *args, **kwargs: value)


def answer_button(monkeypatch, index: int):
    monkeypatch.setattr(mw, "ask_buttons", lambda *args, **kwargs: index)


def last_message() -> str:
    return announcer.last_text


def test_first_rows_are_commands(window):
    assert window.list.item(NEW_ROW).text() == "Neuer Eintrag, Alt+N"
    assert window.list.item(SAVE_ROW).text() == "Speichern"
    assert window.list.currentRow() == NEW_ROW


def test_items_show_only_numbers(window):
    fill(window, "Einleitung", "Problem", "Lösung")
    item = window.list.item(FIRST_SECTION_ROW + 2)
    assert item.text() == "3 Lösung"
    assert item.data(Qt.ItemDataRole.AccessibleTextRole) is None    # NVDA liest den Text


def test_enter_on_new_entry_adds_at_end(window, qtbot, monkeypatch):
    fill(window, "A", "B")
    answer_name(monkeypatch, "C")
    window.list.setCurrentRow(NEW_ROW)
    qtbot.keyClick(window.list, Qt.Key.Key_Return)
    assert names(window) == ["A", "B", "C"]
    assert window.list.section_index() == 2
    assert last_message() == "C angelegt, Position 3"


def test_cancel_name_adds_nothing(window, qtbot, monkeypatch):
    answer_name(monkeypatch, None)
    window.list.setCurrentRow(NEW_ROW)
    qtbot.keyClick(window.list, Qt.Key.Key_Return)
    assert len(window.concept) == 0


def test_alt_n_inserts_below_current(window, qtbot, monkeypatch):
    fill(window, "1", "2", "3", "4", "5")
    answer_name(monkeypatch, "Neu")
    window.list.select_section(3)
    qtbot.keyClick(window.list, Qt.Key.Key_N, Qt.KeyboardModifier.AltModifier)
    assert names(window) == ["1", "2", "3", "4", "Neu", "5"]
    assert window.list.section_index() == 4
    assert window.list.item(FIRST_SECTION_ROW + 5).text() == "6 5"


def test_alt_arrows_move(window, qtbot):
    fill(window, "A", "B", "C")
    window.list.select_section(2)
    qtbot.keyClick(window.list, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    assert names(window) == ["A", "C", "B"]
    assert window.list.section_index() == 1
    assert last_message() == "C, jetzt an Position 2"
    qtbot.keyClick(window.list, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
    qtbot.keyClick(window.list, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
    assert names(window) == ["A", "B", "C"]
    assert last_message() == "Schon ganz unten."


def test_delete_asks_and_cancel_keeps(window, qtbot, monkeypatch):
    fill(window, "A", "B")
    window.list.select_section(0)
    asked = []
    monkeypatch.setattr(mw, "ask_buttons", lambda parent, title, text, *a, **k:
                        asked.append(text) or 1)
    qtbot.keyClick(window.list, Qt.Key.Key_Delete)
    assert asked == ["Abschnitt „A“ löschen?"]
    assert names(window) == ["A", "B"]
    answer_button(monkeypatch, 0)
    qtbot.keyClick(window.list, Qt.Key.Key_Delete)
    assert names(window) == ["B"]
    assert window.list.section_index() == 0
    assert last_message() == "A gelöscht"


def test_delete_last_section_selects_new_entry(window, qtbot, monkeypatch):
    fill(window, "A")
    window.list.select_section(0)
    answer_button(monkeypatch, 0)
    qtbot.keyClick(window.list, Qt.Key.Key_Delete)
    assert window.list.currentRow() == NEW_ROW


def test_f2_renames(window, qtbot, monkeypatch):
    fill(window, "A")
    window.list.select_section(0)
    answer_name(monkeypatch, "Anfang")
    qtbot.keyClick(window.list, Qt.Key.Key_F2)
    assert names(window) == ["Anfang"]
    assert window.list.currentItem().text() == "1 Anfang"


def test_home_end_jump_to_sections(window, qtbot):
    fill(window, "A", "B", "C")
    window.list.setCurrentRow(FIRST_SECTION_ROW + 1)
    qtbot.keyClick(window.list, Qt.Key.Key_Home)
    assert window.list.section_index() == 0
    qtbot.keyClick(window.list, Qt.Key.Key_End)
    assert window.list.section_index() == 2


def test_enter_opens_text_and_escape_returns(window, qtbot):
    fill(window, "A", "B", "C")
    window.list.select_section(1)
    qtbot.keyClick(window.list, Qt.Key.Key_Return)
    assert window.editor.hasFocus()
    assert window.editor.accessibleName() == "Text von 2 B"
    qtbot.keyClicks(window.editor, "Hallo")
    window.list.setCurrentRow(NEW_ROW)              # Liste wurde inzwischen bewegt
    window.editor.setFocus()
    qtbot.keyClick(window.editor, Qt.Key.Key_Escape)
    assert window.list.hasFocus()
    assert window.list.section_index() == 1
    assert window.concept.sections[1].text == "Hallo"
    assert window.concept.modified


def test_keys_in_editor_do_not_touch_list(window, qtbot):
    fill(window, "A", "B")
    window.list.select_section(0)
    window.open_editor()
    qtbot.keyClicks(window.editor, "abc")
    qtbot.keyClick(window.editor, Qt.Key.Key_Home)
    qtbot.keyClick(window.editor, Qt.Key.Key_Delete)
    assert names(window) == ["A", "B"]
    assert window.concept.sections[0].text == "bc"


def test_headings_with_alt_keys(window, qtbot):
    fill(window, "A")
    window.list.select_section(0)
    window.open_editor()
    qtbot.keyClicks(window.editor, "Ziele")
    qtbot.keyClick(window.editor, Qt.Key.Key_1, Qt.KeyboardModifier.AltModifier)
    assert window.concept.sections[0].text == "# Ziele"
    assert last_message() == "Überschrift Ebene 1"
    qtbot.keyClick(window.editor, Qt.Key.Key_3, Qt.KeyboardModifier.AltModifier)
    assert window.concept.sections[0].text == "### Ziele"
    qtbot.keyClick(window.editor, Qt.Key.Key_0, Qt.KeyboardModifier.AltModifier)
    assert window.concept.sections[0].text == "Ziele"
    assert last_message() == "Normaler Text"
    qtbot.keyClicks(window.editor, "!")             # Cursor blieb am Zeilenende
    assert window.concept.sections[0].text == "Ziele!"


def test_moving_open_section_keeps_editor_linked(window, qtbot):
    fill(window, "A", "B")
    window.list.select_section(0)
    window.open_editor()
    window.list.setFocus()
    qtbot.keyClick(window.list, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
    window.editor.setFocus()
    qtbot.keyClicks(window.editor, "x")
    assert window.concept.sections[1].text == "x"
    assert window.concept.sections[0].text == ""


def test_delete_open_section_closes_editor(window, qtbot, monkeypatch):
    fill(window, "A", "B")
    window.list.select_section(0)
    window.open_editor()
    window.list.setFocus()
    answer_button(monkeypatch, 0)
    qtbot.keyClick(window.list, Qt.Key.Key_Delete)
    assert window.editor.section is None
    assert not window.editor.isEnabled()


def test_save_writes_three_files_and_reopens(window, tmp_path, monkeypatch):
    fill(window, "Einleitung", "Lösung")
    window.concept.sections[1].text = "# Kern\nInhalt"
    target = tmp_path / "Plan"
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    assert window.save()
    md = tmp_path / "Plan.konzept"
    assert '"title": "Test"' in md.read_text(encoding="utf-8")
    assert "# Kern" in md.read_text(encoding="utf-8")
    assert (tmp_path / "Plan.pdf").read_bytes().startswith(b"%PDF")
    assert "#" not in (tmp_path / "Plan.txt").read_text(encoding="utf-8")
    assert not window.concept.modified
    assert last_message() == "gespeichert"

    window.new_concept()
    assert len(window.concept) == 0
    assert window.open_file(md)
    assert names(window) == ["Einleitung", "Lösung"]
    assert window.concept.sections[1].text == "# Kern\nInhalt"


def test_title_from_file_name_when_empty(window, tmp_path, monkeypatch):
    window.set_concept(Concept(), None)
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "Idee"), "")))
    window.save()
    assert window.concept.title == "Idee"


def test_autosave_only_with_path_and_changes(window, tmp_path):
    fill(window, "A")
    window.concept.modified = True
    window.autosave()                                # noch kein Speicherort: nichts
    assert not list(tmp_path.glob("*.konzept"))
    window.path = tmp_path / "auto.konzept"
    window.autosave()
    assert (tmp_path / "auto.konzept").is_file()
    assert not window.concept.modified


def test_ask_save_changes(window, monkeypatch):
    fill(window, "A")
    window.concept.modified = True
    answer_button(monkeypatch, 2)                    # Abbrechen
    assert not window.ask_save_changes()
    answer_button(monkeypatch, 1)                    # Nein
    assert window.ask_save_changes()


def test_new_with_changes_cancel_keeps_concept(window, monkeypatch):
    fill(window, "A")
    window.concept.modified = True
    answer_button(monkeypatch, 2)
    window.new_concept()
    assert names(window) == ["A"]


def test_font_size_changes_and_is_remembered(window):
    window.apply_font_size(12)
    window.change_font_size(1)
    assert window.editor.font().pointSize() == 13
    assert int(window.settings.value("font_points")) == 13
    window.change_font_size(0)
    assert window.font_points == mw.DEFAULT_FONT_POINTS


def test_controls_have_names(window):
    assert window.list.accessibleName() == "Abschnitte"
    assert window.editor.accessibleName() == "Text, kein Abschnitt geöffnet"


def test_empty_lines_reach_concept_without_placeholder(window, qtbot):
    fill(window, "A")
    window.concept.sections[0].text = "Eins\n\nDrei"
    window.list.select_section(0)
    window.open_editor()
    qtbot.keyClick(window.editor, Qt.Key.Key_Return)
    qtbot.keyClicks(window.editor, "Vier")
    assert window.concept.sections[0].text == "Eins\n\nDrei\nVier"
    assert "\xa0" not in window.concept.sections[0].text


# -- Unterlisten ----------------------------------------------------------------------------
def right(window, qtbot):
    qtbot.keyClick(window.list, Qt.Key.Key_Right)


def left(window, qtbot):
    qtbot.keyClick(window.list, Qt.Key.Key_Left)


def alt_n(window, qtbot, monkeypatch, name):
    answer_name(monkeypatch, name)
    qtbot.keyClick(window.list, Qt.Key.Key_N, Qt.KeyboardModifier.AltModifier)


def test_right_opens_empty_sublist(window, qtbot):
    fill(window, "Einleitung", "Problem", "Lösung")
    window.list.select_section(2)
    right(window, qtbot)
    assert window.list.count() == 1
    assert window.list.currentItem().text() == EMPTY_TEXT
    assert window.list.accessibleName() == "Unterliste 3.0 Lösung"
    assert last_message() == "Unterliste 3.0 Lösung, leer"


def test_first_sub_entry_and_numbers(window, qtbot, monkeypatch):
    fill(window, "Einleitung", "Problem", "Lösung")
    window.list.select_section(2)
    right(window, qtbot)
    alt_n(window, qtbot, monkeypatch, "Teil A")
    assert window.list.currentItem().text() == "3.1 Teil A"
    assert last_message() == "Teil A angelegt, 3.1"
    alt_n(window, qtbot, monkeypatch, "Teil B")
    assert window.list.currentItem().text() == "3.2 Teil B"
    left(window, qtbot)
    assert window.list.accessibleName() == "Abschnitte"
    assert window.list.currentItem().text() == "3.0 Lösung"


def test_enter_on_empty_row_creates_first_entry(window, qtbot, monkeypatch):
    fill(window, "A")
    window.list.select_section(0)
    right(window, qtbot)
    answer_name(monkeypatch, "Erster")
    qtbot.keyClick(window.list, Qt.Key.Key_Return)
    assert [s.name for s in window.concept.sections[0].children] == ["Erster"]


def test_empty_sublist_leaves_no_marker(window, qtbot):
    fill(window, "A")
    window.list.select_section(0)
    right(window, qtbot)
    left(window, qtbot)
    assert window.list.currentItem().text() == "1 A"


def test_second_level_gets_point_zero(window, qtbot, monkeypatch):
    fill(window, "A", "B", "C")
    window.list.select_section(2)
    right(window, qtbot)
    alt_n(window, qtbot, monkeypatch, "Teil")
    right(window, qtbot)
    assert window.list.accessibleName() == "Unterliste 3.1.0 Teil"
    alt_n(window, qtbot, monkeypatch, "Tief")
    assert window.list.currentItem().text() == "3.1.1 Tief"
    left(window, qtbot)
    assert window.list.currentItem().text() == "3.1.0 Teil"


def test_at_most_four_sublevels(window, qtbot, monkeypatch):
    fill(window, "A")
    window.list.select_section(0)
    for depth in range(4):
        right(window, qtbot)
        alt_n(window, qtbot, monkeypatch, f"Ebene {depth + 1}")
    assert window.list.currentItem().text() == "1.1.1.1.1 Ebene 4"
    right(window, qtbot)
    assert last_message() == "Keine weitere Unterliste möglich."
    assert len(window.level) == 4


def test_left_in_main_list(window, qtbot):
    fill(window, "A")
    left(window, qtbot)
    assert last_message() == "Schon in der Hauptliste."


def test_move_and_delete_inside_sublist(window, qtbot, monkeypatch):
    fill(window, "A")
    window.list.select_section(0)
    right(window, qtbot)
    alt_n(window, qtbot, monkeypatch, "X")
    alt_n(window, qtbot, monkeypatch, "Y")
    qtbot.keyClick(window.list, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    assert [s.name for s in window.concept.sections[0].children] == ["Y", "X"]
    assert last_message() == "Y, jetzt an Position 1"
    answer_button(monkeypatch, 0)
    qtbot.keyClick(window.list, Qt.Key.Key_Delete)
    assert [s.name for s in window.concept.sections[0].children] == ["X"]
    assert names(window) == ["A"]


def test_delete_asks_with_count(window, qtbot, monkeypatch):
    window.set_concept(Concept("T", [Section("A", children=[Section("x"), Section("y")])]),
                       None)
    window.list.select_section(0)
    asked = []
    monkeypatch.setattr(mw, "ask_buttons", lambda parent, title, text, *a, **k:
                        asked.append(text) or 1)
    qtbot.keyClick(window.list, Qt.Key.Key_Delete)
    assert asked == ["Abschnitt „A“ mit 2 Untereinträgen löschen?"]


def test_escape_returns_to_level_of_section(window, qtbot):
    window.set_concept(Concept("T", [Section("A", children=[Section("x"), Section("y")])]),
                       None)
    window.list.select_section(0)
    right(window, qtbot)
    window.list.select_section(1)
    qtbot.keyClick(window.list, Qt.Key.Key_Return)
    assert window.editor.accessibleName() == "Text von 1.2 y"
    window.level = []                                # Liste zeigt inzwischen die Hauptliste
    window.refresh(0)
    window.editor.setFocus()
    qtbot.keyClick(window.editor, Qt.Key.Key_Escape)
    assert window.list.accessibleName() == "Unterliste 1.0 A"
    assert window.list.currentItem().text() == "1.2 y"


def test_save_and_open_keeps_structure(window, tmp_path, monkeypatch):
    window.set_concept(Concept("T", [Section("A", children=[
        Section("x", "Text x", [Section("tief", "ganz unten")])])]), None)
    folders = []

    def fake_save(parent, title, suggestion, *a, **k):
        folders.append(suggestion)
        return str(tmp_path / "Dateien" / "Struktur"), ""
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName", staticmethod(fake_save))
    assert window.save()
    assert folders[0].startswith(str(tmp_path / "Dateien"))   # Vorschlag im Ordner Dateien
    project = tmp_path / "Dateien" / "Struktur.konzept"
    assert project.is_file()
    assert (tmp_path / "Dateien" / "Struktur.pdf").is_file()
    assert "1.1.1 tief" in (tmp_path / "Dateien" / "Struktur.txt").read_text(encoding="utf-8")
    window.new_concept()
    assert window.open_file(project)
    tief = window.concept.sections[0].children[0].children[0]
    assert (tief.name, tief.text) == ("tief", "ganz unten")


def test_old_markdown_opens_without_path(window, tmp_path):
    old = tmp_path / "alt.md"
    old.write_text("# Alt\n\n## Eins\nText\n", encoding="utf-8")
    assert window.open_file(old)
    assert names(window) == ["Eins"]
    assert window.path is None                       # Speichern fragt nach .konzept-Namen
