"""Rechtschreibung: Kern, Unterstreichen, Ton, Ansagen und der Dialog."""
from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCharFormat

from konzeptheft.core.concept import Concept, Section
from konzeptheft.core.spelling import (DELETE_WORD, MyWords, SpellError, Spelling, apply_fix,
                                       word_end_errors)
from konzeptheft.ui import spelling_ui
from konzeptheft.ui.announcer import announcer
from tests.fake_spelling import FakeChecker


@pytest.fixture
def spelling(tmp_path):
    return Spelling(FakeChecker(), MyWords(tmp_path / "woerter.txt"))


# -- Kern -----------------------------------------------------------------------------------------
def test_errors_with_offsets_over_lines(spelling):
    errors = spelling.errors("Ein Tset\nmit Fehlrn")
    assert [(e.word, e.start) for e in errors] == [("Tset", 4), ("Fehlrn", 13)]


def test_repeated_word(spelling):
    errors = spelling.errors("und und")
    assert errors == [SpellError(4, 3, "und", True)]
    assert spelling.suggestions(errors[0]) == [DELETE_WORD]


def test_my_words_are_accepted_and_saved(spelling, tmp_path):
    spelling.my_words.add("Tset")
    assert spelling.errors("Ein Tset") == []
    assert MyWords(tmp_path / "woerter.txt").words() == ["Tset"]
    spelling.my_words.remove(["Tset"])
    assert spelling.errors("Ein Tset") != []


def test_apply_fix():
    text = "Das und und mehr"
    assert apply_fix(text, SpellError(8, 3, "und", True), None) == ("Das und mehr", 7)
    assert apply_fix("Ein Tset.", SpellError(4, 4, "Tset"), "Test") == ("Ein Test.", 8)


def test_word_end(spelling):
    assert word_end_errors(spelling, "Ein Tset", 8)
    assert not word_end_errors(spelling, "Ein Test", 8)


@pytest.mark.skipif(sys.platform != "win32", reason="nur unter Windows")
def test_windows_spell_checker():
    from konzeptheft.core.windows_spelling import WindowsSpellChecker
    try:
        checker = WindowsSpellChecker("de-DE")
    except OSError:
        pytest.skip("Keine deutsche Rechtschreibprüfung in Windows")
    errors = checker.check("Ein Tset mit Fehlrn und und Donaudampfschifffahrt.")
    words = ["Ein Tset mit Fehlrn und und Donaudampfschifffahrt."[e.start:e.start + e.length]
             for e in errors]
    assert words == ["Tset", "Fehlrn", "und"]
    assert "Test" in checker.suggest("Tset")


# -- Im Textfeld ----------------------------------------------------------------------------------
def open_text(window, text: str) -> None:
    window.set_concept(Concept("T", [Section("A", text)]), None)
    window.list.select_section(0)
    window.open_editor()


def test_errors_are_underlined(window):
    open_text(window, "Ein Tset hier")
    formats = window.editor.document().firstBlock().layout().formats()
    wavy = [f for f in formats
            if f.format.underlineStyle() == QTextCharFormat.UnderlineStyle.SpellCheckUnderline]
    assert [(f.start, f.length) for f in wavy] == [(4, 4)]


def test_sound_when_wrong_word_is_finished(window, qtbot):
    open_text(window, "")
    qtbot.keyClicks(window.editor, "Ein Test ")
    assert window.sounds == []
    qtbot.keyClicks(window.editor, "Tset")
    assert window.sounds == []                       # erst wenn das Wort fertig ist
    qtbot.keyClick(window.editor, Qt.Key.Key_Space)
    assert window.sounds == [1]
    qtbot.keyClicks(window.editor, "Fehlrn")
    qtbot.keyClick(window.editor, Qt.Key.Key_Return)
    assert window.sounds == [1, 1]


def test_no_sound_when_switched_off(window, qtbot):
    open_text(window, "")
    window.spell.set_flag(spelling_ui.SOUND_KEY, False)
    qtbot.keyClicks(window.editor, "Tset ")
    assert window.sounds == []


def test_line_with_errors_is_announced(window, qtbot):
    open_text(window, "Gut\nEin Tset und Fehlrn")
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    window.editor.setTextCursor(cursor)
    qtbot.keyClick(window.editor, Qt.Key.Key_Down)
    assert announcer.last_text == "Fehler: Tset, Fehlrn"


def test_word_with_error_is_announced(window, qtbot):
    open_text(window, "Ein Tset hier")
    cursor = window.editor.textCursor()
    cursor.setPosition(0)
    window.editor.setTextCursor(cursor)
    qtbot.keyClick(window.editor, Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier)
    assert announcer.last_text == "Rechtschreibfehler"


def test_opening_section_announces_count(window):
    open_text(window, "Tset und Fehlrn")
    assert announcer.last_text == "2 Rechtschreibfehler"


# -- Dialog -----------------------------------------------------------------------------------------
def script_dialog(monkeypatch, *steps):
    """Ersetzt exec: führt Schritte im Dialog aus. Jeder Schritt bekommt den Dialog."""
    seen = []

    def fake_exec(dialog):
        for step in steps:
            if dialog.current is not None:
                seen.append(dialog.field.text())
            step(dialog)
            if dialog.result():
                break
        return dialog.result()
    monkeypatch.setattr(spelling_ui.SpellDialog, "exec", fake_exec)
    return seen


def check(row: int):
    def step(dialog):
        dialog.suggestions.item(row).setCheckState(Qt.CheckState.Checked)
        dialog.next_button.click()
    return step


def press_next(dialog):
    dialog.next_button.click()


def test_whole_concept_with_suggestion_typed_word_and_skip(window, monkeypatch):
    window.set_concept(Concept("T", [Section("A", "Ein Tset."),
                                     Section("B", "Fehlrn hier", [Section("C", "Konzpt da")])]),
                       None)

    def type_word(dialog):
        dialog.field.setText("Fehler")
        dialog.next_button.click()

    seen = script_dialog(monkeypatch, check(0), type_word, press_next)
    window.spell.check_concept()
    assert seen == ["Tset", "Fehlrn", "Konzpt"]
    texts = [s.text for _n, s in window.concept.walk()]
    assert texts == ["Ein Test.", "Fehler hier", "Konzpt da"]
    assert window.concept.modified
    assert announcer.last_text == "Rechtschreibprüfung abgeschlossen."


def test_only_one_suggestion_checked(window, monkeypatch):
    window.set_concept(Concept("T", [Section("A", "Tset")]), None)

    def two_checks(dialog):
        dialog.suggestions.item(0).setCheckState(Qt.CheckState.Checked)
        dialog.suggestions.item(1).setCheckState(Qt.CheckState.Checked)
        assert dialog.suggestions.item(0).checkState() == Qt.CheckState.Unchecked
        dialog.next_button.click()

    script_dialog(monkeypatch, two_checks)
    window.spell.check_concept()
    assert window.concept.sections[0].text == "Stet"


def test_add_to_dictionary_then_remove(window, monkeypatch):
    window.set_concept(Concept("T", [Section("A", "Tset und Tset")]), None)
    script_dialog(monkeypatch, lambda d: d.add_button.click())
    window.spell.check_concept()
    assert window.spell.spelling.my_words.words() == ["Tset"]
    assert window.concept.sections[0].text == "Tset und Tset"     # zweites wird nicht gefragt

    def uncheck_and_close(dialog):
        dialog.words.item(0).setCheckState(Qt.CheckState.Unchecked)
        dialog.close_button.click()

    script_dialog(monkeypatch, uncheck_and_close)
    window.spell.edit_my_words()
    assert window.spell.spelling.my_words.words() == []


def test_delete_repeated_word(window, monkeypatch):
    window.set_concept(Concept("T", [Section("A", "Das und und mehr")]), None)
    script_dialog(monkeypatch, check(0))
    window.spell.check_concept()
    assert window.concept.sections[0].text == "Das und mehr"


def test_fix_in_open_editor_with_empty_lines(window, monkeypatch):
    open_text(window, "Eins\n\nEin Tset")
    script_dialog(monkeypatch, check(0))
    window.spell.check_concept()
    assert window.editor.text() == "Eins\n\nEin Test"
    assert window.concept.sections[0].text == "Eins\n\nEin Test"


def test_alt_r_on_word_at_cursor(window, qtbot, monkeypatch):
    open_text(window, "Ein Tset und Fehlrn")
    cursor = window.editor.textCursor()
    cursor.setPosition(6)                            # mitten in Tset
    window.editor.setTextCursor(cursor)
    seen = script_dialog(monkeypatch, check(0))
    qtbot.keyClick(window.editor, Qt.Key.Key_R, Qt.KeyboardModifier.AltModifier)
    assert seen == ["Tset"]
    assert window.concept.sections[0].text == "Ein Test und Fehlrn"
    assert window.editor.textCursor().position() == 8


def test_alt_r_without_error(window, qtbot):
    open_text(window, "Alles gut")
    qtbot.keyClick(window.editor, Qt.Key.Key_R, Qt.KeyboardModifier.AltModifier)
    assert announcer.last_text == "Kein Rechtschreibfehler."


def test_no_errors_in_concept(window):
    window.set_concept(Concept("T", [Section("A", "Alles gut")]), None)
    window.spell.check_concept()
    assert announcer.last_text == "Keine Rechtschreibfehler."


def test_dialog_tab_order_and_names(window, monkeypatch):
    window.set_concept(Concept("T", [Section("A", "Tset")]), None)
    found = {}

    def inspect(dialog):
        found["names"] = [dialog.field.accessibleName(), dialog.suggestions.accessibleName(),
                          dialog.words.accessibleName()]
        order, widget = [], dialog.field
        for _ in range(5):
            widget = widget.nextInFocusChain()
            while not widget.focusPolicy() & Qt.FocusPolicy.TabFocus:
                widget = widget.nextInFocusChain()
            order.append(widget)
        found["order"] = order[:5]
        found["expected"] = [dialog.suggestions, dialog.next_button, dialog.add_button,
                             dialog.close_button, dialog.words]
        dialog.close_button.click()

    script_dialog(monkeypatch, inspect)
    window.spell.check_concept()
    assert found["names"] == ["Wort", "Vorschläge", "Meine Wörter"]
    assert found["order"] == found["expected"]


def test_without_windows_spelling(window, monkeypatch):
    window.spell.spelling = None
    window.spell.check_concept()
    assert "keine deutsche Rechtschreibprüfung" in announcer.last_text
