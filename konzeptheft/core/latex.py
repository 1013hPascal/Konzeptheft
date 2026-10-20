"""LaTeX-Ausgabe (.tex) mit einem übersichtlichen Kopf für deutsche Texte.

Die Abschnitte werden Gliederungsbefehle: Hauptliste \\section, erste Unterliste \\subsection,
dann \\subsubsection, \\paragraph und \\subparagraph. LaTeX nummeriert selbst und kommt dabei auf
dieselben Nummern wie das Konzeptheft (1, 1.1, 1.1.1 ...).

Überschriften im Text eines Abschnitts (Alt+1 bis Alt+3) werden Befehle mit Stern, eine Ebene
unter dem Abschnitt. Sie haben keine Nummer, damit die Nummern der Abschnitte stimmen.
Listen im Text ("- ", "* ", "1. ") werden itemize und enumerate, auch verschachtelt (blocks.py).
"""
from __future__ import annotations

import re

from konzeptheft import APP_NAME
from konzeptheft.core.blocks import Heading, ListBlock, parse
from konzeptheft.core.concept import Concept

SECTION_COMMANDS = ["section", "subsection", "subsubsection", "paragraph", "subparagraph"]

PREAMBLE = r"""% Erstellt mit dem Konzeptheft. Übersetzen mit pdflatex oder lualatex.
\documentclass[11pt,a4paper,parskip=half,numbers=noenddot]{scrartcl}

% Sprache und Schrift
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[ngerman]{babel}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage[autostyle=true,german=quotes]{csquotes}

% Seite
\usepackage[a4paper,margin=2.5cm]{geometry}

% Tabellen, Listen, Grafiken, Farben
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{longtable}
\usepackage{enumitem}
\usepackage{graphicx}
\usepackage{xcolor}

% Mathematik und Einheiten
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{siunitx}
\sisetup{locale=DE}

% Verweise und PDF-Lesezeichen (zuletzt laden)
\usepackage[hidelinks,bookmarksnumbered]{hyperref}

% Nummern und Inhaltsverzeichnis bis zur fünften Ebene
\setcounter{secnumdepth}{5}
\setcounter{tocdepth}{5}
% \paragraph und \subparagraph als eigene Zeile statt im Text
\RedeclareSectionCommand[afterskip=0.5\baselineskip,beforeskip=1\baselineskip]{paragraph}
\RedeclareSectionCommand[afterskip=0.5\baselineskip,beforeskip=1\baselineskip,indent=0pt]{subparagraph}
"""

_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    '"': r"\textquotedbl{}",            # mit ngerman ist " sonst ein Kurzbefehl
    " ": "~",                      # geschütztes Leerzeichen
}
_SPECIAL_RE = re.compile("|".join(re.escape(c) for c in _SPECIAL))


def escape(text: str) -> str:
    """Zeichen, die in LaTeX eine Bedeutung haben, als normalen Text schreiben."""
    return _SPECIAL_RE.sub(lambda m: _SPECIAL[m.group(0)], text)


def _command(index: int, title: str, numbered: bool) -> str:
    name = SECTION_COMMANDS[min(index, len(SECTION_COMMANDS) - 1)]
    return f"\\{name}{'' if numbered else '*'}{{{escape(title)}}}"


def _list(block: ListBlock, indent: str = "") -> list[str]:
    """Liste als itemize (Punkte) oder enumerate (Nummern), Unterlisten eingerückt."""
    env = "enumerate" if block.ordered else "itemize"
    out = [f"{indent}\\begin{{{env}}}"]
    for item in block.items:
        out.append(f"{indent}  \\item {escape(item.text)}")
        if item.sub is not None:
            out += _list(item.sub, indent + "    ")
    out.append(f"{indent}\\end{{{env}}}")
    return out


def _body(text: str, depth: int) -> list[str]:
    """Absätze, Listen und Text-Überschriften eines Abschnitts. Zeilen eines Absatzes werden mit
    \\\\ getrennt, damit die Zeilenumbrüche erhalten bleiben."""
    out: list[str] = []
    for block in parse(text):
        if isinstance(block, Heading):
            out.append(_command(depth + block.level, block.text, numbered=False))
        elif isinstance(block, ListBlock):
            out += _list(block)
        else:
            out.append(" \\\\\n".join(escape(line) for line in block.lines))
        out.append("")
    return out


def to_latex(concept: Concept) -> str:
    lines = [PREAMBLE]
    lines.append(f"\\title{{{escape(concept.title)}}}" if concept.title else "\\title{Konzept}")
    lines += ["\\author{}", "\\date{\\today}","\\hypersetup{pdftitle={%s}, pdfcreator={%s}}"
              % (escape(concept.title), APP_NAME), "",
              "\\begin{document}", "", "\\maketitle", "\\tableofcontents", ""]
    for numbers, section in concept.walk():
        depth = len(numbers) - 1
        lines.append(f"% {'.'.join(str(n) for n in numbers)}")
        lines.append(_command(depth, section.name, numbered=True))
        lines.append("")
        lines += _body(section.text, depth)
    lines.append("\\end{document}")
    return "\n".join(lines) + "\n"
