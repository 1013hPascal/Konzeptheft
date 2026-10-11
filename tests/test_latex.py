"""LaTeX-Ausgabe: Kopf, Gliederung, Sonderzeichen, Menüpunkt."""
from __future__ import annotations

from konzeptheft.core import storage
from konzeptheft.core.concept import Concept, Section
from konzeptheft.core.latex import escape, to_latex
from konzeptheft.ui import main_window as mw


def sample() -> Concept:
    tief = Section("E4", "ganz unten\n# Notiz")
    for name in ("E3", "E2", "E1"):
        tief = Section(name, children=[tief])
    return Concept("Mein Plan", [Section("Einleitung", "Zeile 1\nZeile 2\n\nNeuer Absatz\n# Idee"),
                                 tief])


def test_preamble_for_german():
    tex = to_latex(sample())
    for needed in (r"\usepackage[utf8]{inputenc}", r"\usepackage[ngerman]{babel}",
                   r"\usepackage[T1]{fontenc}", r"\usepackage{booktabs}",
                   "{csquotes}", r"\begin{document}",
                   r"\maketitle", r"\tableofcontents", r"\end{document}"):
        assert needed in tex
    assert r"\title{Mein Plan}" in tex


def test_levels_become_section_commands():
    tex = to_latex(sample())
    assert r"\section{Einleitung}" in tex
    assert r"\section{E1}" in tex
    assert r"\subsection{E2}" in tex
    assert r"\subsubsection{E3}" in tex
    assert r"\paragraph{E4}" in tex


def test_text_headings_are_unnumbered_one_level_down():
    tex = to_latex(sample())
    assert r"\subsection*{Idee}" in tex
    assert r"\subparagraph*{Notiz}" in tex


def test_lines_and_paragraphs():
    tex = to_latex(sample())
    assert "Zeile 1 \\\\\nZeile 2\n\nNeuer Absatz" in tex


def test_escape_special_characters():
    assert escape(r'50 % & $5 #1 a_b {x} ~ ^ \ "z"') == (
        r"50 \% \& \$5 \#1 a\_b \{x\} \textasciitilde{} \textasciicircum{} "
        r"\textbackslash{} \textquotedbl{}z\textquotedbl{}")
    assert escape("Größe ä ß") == "Größe ä ß"


def test_save_latex(tmp_path):
    path = storage.latex_path(tmp_path / "Plan 1.2")
    assert path.name == "Plan 1.2.tex"
    storage.save_latex(path, sample())
    assert path.read_text(encoding="utf-8").startswith("% Erstellt mit dem Konzeptheft")


def test_menu_export(window, tmp_path, monkeypatch):
    window.set_concept(sample(), None)
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "Export"), "")))
    assert window.export_latex()
    assert (tmp_path / "Export.tex").is_file()
    assert mw.announcer.last_text == "Export.tex exportiert"
