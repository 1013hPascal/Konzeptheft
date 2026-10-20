"""Word-Ausgabe (.docx), ohne zusätzliche Bibliothek.

Eine .docx-Datei ist eine ZIP-Datei mit XML-Dateien (Office Open XML). Hier werden nur die
nötigen Teile geschrieben: Dokument, Formatvorlagen, Nummerierung und Dokumenteigenschaften.

- Der Titel bekommt die Formatvorlage "Titel" und ist keine Überschrift.
- Die Abschnitte werden echte Word-Überschriften: Hauptliste "Überschrift 1", erste Unterliste
  "Überschrift 2" und so weiter. So springt man in Word mit NVDA (Taste H) und im
  Navigationsbereich durch die Gliederung. Die Nummer steht wie in der PDF vor dem Namen.
- Überschriften im Text liegen eine Ebene unter dem Abschnitt.
- Listen werden echte Word-Listen mit Aufzählungszeichen oder Nummern, auch verschachtelt. Jede
  nummerierte Liste beginnt wieder bei 1.
- Sprache des Dokuments ist Deutsch, damit Word richtig prüft und NVDA richtig vorliest.
"""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from konzeptheft import APP_NAME
from konzeptheft.core.blocks import Heading, ListBlock, parse
from konzeptheft.core.concept import Concept, export_number

MAX_HEADING = 9
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
BULLET_NUM = 1                          # gemeinsame Nummerierung für alle Aufzählungen
BULLETS = ["•", "◦", "▪", "•", "◦", "▪", "•", "◦",
           "▪"]


def _text(text: str) -> str:
    return f'<w:t xml:space="preserve">{escape(text)}</w:t>'


def _paragraph(style: str | None, runs: str, numbering: tuple[int, int] | None = None) -> str:
    props = ""
    if style or numbering:
        props = "<w:pPr>"
        if style:
            props += f'<w:pStyle w:val="{style}"/>'
        if numbering:
            num, level = numbering
            props += f'<w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="{num}"/></w:numPr>'
        props += "</w:pPr>"
    return f"<w:p>{props}<w:r>{runs}</w:r></w:p>"


class _Writer:
    def __init__(self) -> None:
        self.body: list[str] = []
        self.ordered_lists = 0          # jede nummerierte Liste bekommt eine eigene Nummerierung

    def heading(self, level: int, text: str) -> None:
        self.body.append(_paragraph(f"Heading{min(level, MAX_HEADING)}", _text(text)))

    def lines(self, lines: list[str]) -> None:
        runs = "<w:br/>".join(_text(line) for line in lines)
        self.body.append(_paragraph(None, runs))

    def list(self, block: ListBlock, level: int = 0, num: int | None = None) -> None:
        if num is None:
            if block.ordered:
                self.ordered_lists += 1
                num = BULLET_NUM + self.ordered_lists
            else:
                num = BULLET_NUM
        for item in block.items:
            self.body.append(_paragraph("ListParagraph", _text(item.text), (num, level)))
            if item.sub is not None:
                same_kind = item.sub.ordered == block.ordered
                self.list(item.sub, level + 1, num if same_kind else None)


def _document(concept: Concept) -> tuple[str, int]:
    writer = _Writer()
    if concept.title:
        writer.body.append(_paragraph("Title", _text(concept.title)))
    for numbers, section in concept.walk():
        depth = len(numbers) - 1
        writer.heading(depth + 1, f"{export_number(numbers)} {section.name}")
        for block in parse(section.text):
            if isinstance(block, Heading):
                writer.heading(depth + 1 + block.level, block.text)
            elif isinstance(block, ListBlock):
                writer.list(block)
            else:
                writer.lines(block.lines)
    section_props = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                     '<w:pgMar w:top="1417" w:right="1417" w:bottom="1134" w:left="1417" '
                     'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')
    xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document xmlns:w="{W}"><w:body>{"".join(writer.body)}{section_props}'
           f'</w:body></w:document>')
    return xml, writer.ordered_lists


def _styles() -> str:
    headings = []
    sizes = [32, 28, 26, 24, 24, 22, 22, 22, 22]               # halbe Punkt
    for level in range(1, MAX_HEADING + 1):
        size = sizes[level - 1]
        italic = "<w:i/>" if level >= 4 else ""
        headings.append(
            f'<w:style w:type="paragraph" w:styleId="Heading{level}">'
            f'<w:name w:val="heading {level}"/><w:basedOn w:val="Normal"/>'
            f'<w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/>'
            f'<w:pPr><w:keepNext/><w:spacing w:before="{360 if level == 1 else 240}" '
            f'w:after="80"/><w:outlineLvl w:val="{level - 1}"/></w:pPr>'
            f'<w:rPr><w:b/>{italic}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
            f'</w:style>')
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:styles xmlns:w="{W}">'
        '<w:docDefaults><w:rPrDefault><w:rPr>'
        '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/>'
        '<w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="de-DE" w:eastAsia="en-US" '
        'w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="259" w:lineRule="auto"/>'
        '</w:pPr></w:pPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:after="240"/></w:pPr>'
        '<w:rPr><w:b/><w:sz w:val="44"/><w:szCs w:val="44"/></w:rPr></w:style>'
        + "".join(headings) +
        '<w:style w:type="paragraph" w:styleId="ListParagraph">'
        '<w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:after="60"/><w:contextualSpacing/></w:pPr></w:style>'
        '</w:styles>')


def _levels(ordered: bool) -> str:
    out = []
    for level in range(9):
        indent = 720 + level * 360
        if ordered:
            fmt, text = "decimal", f"%{level + 1}."
        else:
            fmt, text = "bullet", BULLETS[level]
        out.append(f'<w:lvl w:ilvl="{level}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/>'
                   f'<w:lvlText w:val="{escape(text)}"/><w:lvlJc w:val="left"/>'
                   f'<w:pPr><w:ind w:left="{indent}" w:hanging="360"/></w:pPr></w:lvl>')
    return "".join(out)


def _numbering(ordered_lists: int) -> str:
    nums = [f'<w:num w:numId="{BULLET_NUM}"><w:abstractNumId w:val="0"/></w:num>']
    for index in range(ordered_lists):
        num_id = BULLET_NUM + 1 + index
        restart = "".join(f'<w:lvlOverride w:ilvl="{lvl}"><w:startOverride w:val="1"/>'
                          f'</w:lvlOverride>' for lvl in range(9))
        nums.append(f'<w:num w:numId="{num_id}"><w:abstractNumId w:val="1"/>{restart}</w:num>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:numbering xmlns:w="{W}">'
            f'<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>'
            f'{_levels(False)}</w:abstractNum>'
            f'<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>'
            f'{_levels(True)}</w:abstractNum>'
            + "".join(nums) + '</w:numbering>')


CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.numbering+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-'
    'package.core-properties+xml"/>'
    '</Types>')

PACKAGE_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
    'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '</Relationships>')

DOCUMENT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/styles" Target="styles.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/numbering" Target="numbering.xml"/>'
    '</Relationships>')


def _core(title: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
            'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:language>de-DE</dc:language>'
            f'<cp:lastModifiedBy>{APP_NAME}</cp:lastModifiedBy>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            '</cp:coreProperties>')


def to_docx_bytes(concept: Concept) -> bytes:
    import io
    document, ordered_lists = _document(concept)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", CONTENT_TYPES)
        package.writestr("_rels/.rels", PACKAGE_RELS)
        package.writestr("word/document.xml", document)
        package.writestr("word/styles.xml", _styles())
        package.writestr("word/numbering.xml", _numbering(ordered_lists))
        package.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        package.writestr("docProps/core.xml", _core(concept.title))
    return buffer.getvalue()


def write_docx(path: Path, concept: Concept) -> None:
    path.write_bytes(to_docx_bytes(concept))
