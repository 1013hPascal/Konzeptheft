"""Listen im Text, Word-Ausgabe, Listen in LaTeX und PDF, Alt+T."""
from __future__ import annotations

import zipfile
from xml.dom import minidom

from PySide6.QtCore import Qt

from konzeptheft.core import storage
from konzeptheft.core.blocks import Heading, ListBlock, Paragraph, parse
from konzeptheft.core.concept import Concept, Section
from konzeptheft.core.docx import to_docx_bytes
from konzeptheft.core.export import to_html
from konzeptheft.core.latex import to_latex
from konzeptheft.ui import main_window as mw

TEXT = "Erste Zeile\nzweite Zeile\n\n- Punkt A\n  - Unter A1\n- Punkt B\n1. Eins\n2) Zwei\n# Idee\nSchluss"


def sample() -> Concept:
    return Concept("Plan & Ziel", [Section("Einleitung", TEXT),
                                   Section("Lösung", "", [Section("Teil", "* nur ein Punkt")])])


# -- Bausteine ------------------------------------------------------------------------------------
def test_parse_blocks():
    blocks = parse(TEXT)
    assert isinstance(blocks[0], Paragraph) and blocks[0].lines == ["Erste Zeile", "zweite Zeile"]
    bullets, numbers, heading, last = blocks[1:]
    assert isinstance(bullets, ListBlock) and not bullets.ordered
    assert [i.text for i in bullets.items] == ["Punkt A", "Punkt B"]
    assert [i.text for i in bullets.items[0].sub.items] == ["Unter A1"]
    assert isinstance(numbers, ListBlock) and numbers.ordered
    assert [i.text for i in numbers.items] == ["Eins", "Zwei"]
    assert heading == Heading(1, "Idee")
    assert last == Paragraph(["Schluss"])


def test_text_after_list_is_paragraph():
    blocks = parse("- a\nkein Punkt")
    assert isinstance(blocks[0], ListBlock) and blocks[1] == Paragraph(["kein Punkt"])


def test_deep_lists_are_capped():
    blocks = parse("- 1\n  - 2\n    - 3\n      - 4\n        - 5")
    level, block = 1, blocks[0]
    while block.items[0].sub is not None:
        block, level = block.items[0].sub, level + 1
    assert level == 4 and [i.text for i in block.items] == ["4", "5"]


# -- LaTeX und PDF ----------------------------------------------------------------------------------
def test_latex_lists():
    tex = to_latex(sample())
    assert "\\begin{itemize}\n  \\item Punkt A\n    \\begin{itemize}\n      \\item Unter A1" in tex
    assert "\\begin{enumerate}\n  \\item Eins\n  \\item Zwei\n\\end{enumerate}" in tex
    assert "\\subsection*{Idee}" in tex
    assert "\\subsection{Teil}" in tex


def test_pdf_html_lists():
    html = to_html(sample())
    assert "<ul><li>Punkt A<ul><li>Unter A1</li></ul></li><li>Punkt B</li></ul>" in html
    assert "<ol><li>Eins</li><li>Zwei</li></ol>" in html


# -- Word -------------------------------------------------------------------------------------------
def read_docx(data: bytes) -> dict[str, str]:
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        return {name: package.read(name).decode("utf-8") for name in package.namelist()}


def test_docx_parts_are_valid_xml():
    parts = read_docx(to_docx_bytes(sample()))
    for name in ("[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/styles.xml",
                 "word/numbering.xml", "word/_rels/document.xml.rels", "docProps/core.xml"):
        minidom.parseString(parts[name])                  # wirft bei kaputtem XML


def paragraphs(document: str) -> list[tuple[str, str, str]]:
    """(Formatvorlage, Liste:Ebene, Text) je Absatz."""
    dom = minidom.parseString(document)
    out = []
    for p in dom.getElementsByTagName("w:p"):
        style = p.getElementsByTagName("w:pStyle")
        num = p.getElementsByTagName("w:numId")
        level = p.getElementsByTagName("w:ilvl")
        text = "|".join(t.firstChild.data if t.firstChild else ""
                        for t in p.getElementsByTagName("w:t"))
        out.append((style[0].getAttribute("w:val") if style else "",
                    f"{num[0].getAttribute('w:val')}:{level[0].getAttribute('w:val')}"
                    if num else "", text))
    return out


def test_docx_structure():
    parts = read_docx(to_docx_bytes(sample()))
    assert paragraphs(parts["word/document.xml"]) == [
        ("Title", "", "Plan & Ziel"),
        ("Heading1", "", "1. Einleitung"),
        ("", "", "Erste Zeile|zweite Zeile"),
        ("ListParagraph", "1:0", "Punkt A"),
        ("ListParagraph", "1:1", "Unter A1"),
        ("ListParagraph", "1:0", "Punkt B"),
        ("ListParagraph", "2:0", "Eins"),
        ("ListParagraph", "2:0", "Zwei"),
        ("Heading2", "", "Idee"),
        ("", "", "Schluss"),
        ("Heading1", "", "2. Lösung"),
        ("Heading2", "", "2.1 Teil"),
        ("ListParagraph", "1:0", "nur ein Punkt"),
    ]
    assert "<w:br/>" in parts["word/document.xml"]
    assert 'w:lang w:val="de-DE"' in parts["word/styles.xml"]
    assert '<w:outlineLvl w:val="0"/>' in parts["word/styles.xml"]
    assert "<dc:title>Plan &amp; Ziel</dc:title>" in parts["docProps/core.xml"]


def test_each_numbered_list_starts_at_one():
    concept = Concept("T", [Section("A", "1. a\n\n1. b")])
    parts = read_docx(to_docx_bytes(concept))
    nums = [n for _s, n, _t in paragraphs(parts["word/document.xml"]) if n]
    assert nums == ["2:0", "3:0"]
    assert parts["word/numbering.xml"].count("<w:startOverride") == 18


def test_save_docx(tmp_path):
    path = storage.docx_path(tmp_path / "Plan 1.2")
    assert path.name == "Plan 1.2.docx"
    storage.save_docx(path, sample())
    assert zipfile.is_zipfile(path)
    assert not list(tmp_path.glob("*.tmp"))


# -- Menü -------------------------------------------------------------------------------------------
def test_word_export_from_menu(window, tmp_path, monkeypatch):
    window.set_concept(sample(), None)
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "Export"), "")))
    window.list.setFocus()
    assert window.export_word()
    assert (tmp_path / "Export.docx").is_file()
    assert mw.announcer.last_text == "Export.docx exportiert"
    assert window.list.hasFocus()


def test_alt_t_opens_title(window, qtbot, monkeypatch):
    asked = []
    monkeypatch.setattr(mw, "ask_name", lambda parent, title, label, text="":
                        asked.append(label) or "Neuer Titel")
    qtbot.keyClick(window.list, Qt.Key.Key_T, Qt.KeyboardModifier.AltModifier)
    assert asked == ["&Titel des Konzepts:"]
    assert window.concept.title == "Neuer Titel"
