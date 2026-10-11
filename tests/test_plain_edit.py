"""Textfeld: leere Zeilen, Enter, Entf, Pfeiltasten und die Zeile, die NVDA bekommt."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from konzeptheft.ui.common import EMPTY_LINE, PARAGRAPH_SEPARATOR, PlainEdit


def uia_line(edit: PlainEdit) -> str:
    """Nachbau von QWindowsUiaTextRangeProvider::ExpandToEnclosingUnit(TextUnit_Line) aus
    qtbase 6.11: Diese Zeile liest NVDA an der Cursorposition vor und zeigt sie in Braille."""
    cursor = QTextCursor(edit.document())
    cursor.select(QTextCursor.SelectionType.Document)
    text = cursor.selectedText().replace(PARAGRAPH_SEPARATOR, "\n")
    length = len(text)
    if length < 1:
        return ""
    start_offset = edit.textCursor().position()
    start = start_offset if 0 <= start_offset < length else length - 1
    for t in range(start, -1, -1):
        if text[t] != "\n" and (t == 0 or text[t - 1] == "\n"):
            start_offset = t
            break
    end_offset = start_offset
    for t in range(start_offset, length):
        if t == length - 1 or (text[t] == "\n" and text[t + 1] != "\n"):
            end_offset = t + 1
            break
    return text[start_offset:end_offset].rstrip("\n")


@pytest.fixture
def edit(qtbot):
    widget = PlainEdit()
    qtbot.addWidget(widget)
    widget.show()
    widget.setFocus()
    return widget


def test_enter_at_end_reports_new_empty_line(edit, qtbot):
    qtbot.keyClicks(edit, "Hallo")
    assert uia_line(edit) == "Hallo"
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    assert uia_line(edit) == EMPTY_LINE                # NVDA: "leer", nicht mehr "Hallo"
    qtbot.keyClicks(edit, "W")
    assert uia_line(edit) == "W"
    assert edit.text() == "Hallo\nW"


def test_empty_line_in_the_middle(edit, qtbot):
    edit.set_text("Eins\n\nDrei")
    cursor = edit.textCursor()
    cursor.setPosition(edit.document().findBlockByNumber(1).position())
    edit.setTextCursor(cursor)
    assert uia_line(edit) == EMPTY_LINE
    assert edit.text() == "Eins\n\nDrei"


def test_typing_at_end_of_upper_line_stays_there(edit, qtbot):
    edit.set_text("Hallo\n")
    cursor = edit.textCursor()
    cursor.setPosition(5)
    edit.setTextCursor(cursor)
    qtbot.keyClicks(edit, "!")
    assert edit.text() == "Hallo!\n"
    assert uia_line(edit) == "Hallo!"
    assert edit.textCursor().blockNumber() == 0


def test_typing_on_empty_line_removes_placeholder(edit, qtbot):
    qtbot.keyClicks(edit, "A")
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    qtbot.keyClicks(edit, "bc")
    assert edit.document().findBlockByNumber(1).text() == "bc"
    assert edit.textCursor().positionInBlock() == 2


def test_backspace_on_empty_line_goes_back_to_end_of_previous(edit, qtbot):
    qtbot.keyClicks(edit, "Hallo")
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    qtbot.keyClick(edit, Qt.Key.Key_Backspace)
    assert edit.text() == "Hallo"
    assert edit.document().toRawText() == "Hallo"
    assert edit.textCursor().position() == 5


def test_delete_on_empty_line_pulls_next_line_up(edit, qtbot):
    edit.set_text("A\n\nB")
    cursor = edit.textCursor()
    cursor.setPosition(edit.document().findBlockByNumber(1).position())
    edit.setTextCursor(cursor)
    qtbot.keyClick(edit, Qt.Key.Key_Delete)
    assert edit.text() == "A\nB"
    assert edit.textCursor().block().text() == "B"
    assert edit.textCursor().positionInBlock() == 0


def test_delete_at_end_of_line_before_empty_line(edit, qtbot):
    edit.set_text("A\n\nB")
    cursor = edit.textCursor()
    cursor.setPosition(1)
    edit.setTextCursor(cursor)
    qtbot.keyClick(edit, Qt.Key.Key_Delete)
    assert edit.text() == "A\nB"


def test_arrows_never_stop_behind_placeholder(edit, qtbot):
    edit.set_text("A\n\nB")
    cursor = edit.textCursor()
    cursor.setPosition(1)                             # Ende von A
    edit.setTextCursor(cursor)
    qtbot.keyClick(edit, Qt.Key.Key_Right)
    assert (edit.textCursor().blockNumber(), edit.textCursor().positionInBlock()) == (1, 0)
    qtbot.keyClick(edit, Qt.Key.Key_Right)             # wie in Word: gleich zur nächsten Zeile
    assert (edit.textCursor().blockNumber(), edit.textCursor().positionInBlock()) == (2, 0)
    qtbot.keyClick(edit, Qt.Key.Key_Left)
    assert (edit.textCursor().blockNumber(), edit.textCursor().positionInBlock()) == (1, 0)
    qtbot.keyClick(edit, Qt.Key.Key_End)
    assert edit.textCursor().positionInBlock() == 0


def test_undo_removes_enter_completely(edit, qtbot):
    qtbot.keyClicks(edit, "Hallo")
    qtbot.keyClick(edit, Qt.Key.Key_Return)
    edit.undo()
    assert edit.document().toRawText() == "Hallo"


def test_only_one_line_has_no_placeholder(edit, qtbot):
    qtbot.keyClicks(edit, "x")
    qtbot.keyClick(edit, Qt.Key.Key_Backspace)
    assert edit.document().toRawText() == ""


def test_shift_enter_and_paste_give_real_lines(edit, qtbot):
    qtbot.keyClicks(edit, "a")
    qtbot.keyClick(edit, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert uia_line(edit) == EMPTY_LINE
    assert edit.text() == "a\n"


def test_copy_has_no_placeholder(edit):
    edit.set_text("A\n\nB")
    edit.selectAll()
    assert edit.createMimeDataFromSelection().text() == "A\n\nB"


def test_real_nbsp_inside_text_is_kept(edit, qtbot):
    edit.set_text(f"z.{EMPTY_LINE}B.\nx")
    assert edit.text() == f"z.{EMPTY_LINE}B.\nx"
