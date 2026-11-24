"""Build the editable Word manuscript from ``research_paper/src``.

Renders headings, paragraphs, lists, pipe tables, figures and captions into a
single A4 DOCX with an automatic table of contents, a style-driven list of
figures and list of tables, running header, page numbers, and IEEE-style
reference entries. Inputs are the Markdown sources only; nothing outside
``research_paper/`` is written.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PAPER = Path(__file__).resolve().parents[1]
SRC = PAPER / "src"
OUT = PAPER / "FLY_SURFER_COMPLETE_RESEARCH_PAPER.docx"

TITLE = ("Teaching a Fruit Fly Brain to Play Subway Surfers Through "
         "Connectome-Based Neural Simulation")
SHORT_TITLE = "Teaching a Fruit Fly Brain to Play Subway Surfers"

FIGURE_RE = re.compile(r"^!\[Figure (\d+)\. (.*?)\]\((figures/[^)]+)\)\s*$")
TABLE_CAP_RE = re.compile(r"^\*\*(Table [0-9]+|[A-K][0-9]+)\.\*\* (.*)$")
HEADING_RE = re.compile(r"^(#{1,3}) (.*)$")
BULLET_RE = re.compile(r"^[-*] (.*)$")
NUMBERED_RE = re.compile(r"^(\d+)\. (.*)$")
EQUATION_TAIL = re.compile(r"\(\d+(?:\.\d+)*\)$")
PIPETABLE_SEP = re.compile(r"^\|?[\s:|-]+\|[\s:|-]*$")
INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)")
FRONT_HEADINGS = {"Abstract", "Abbreviations and terminology", "Table of contents",
                  "List of figures", "List of tables"}


def set_cell_shading(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def add_field(paragraph, instr: str, placeholder: str = "") -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    run._r.append(begin)
    run2 = paragraph.add_run()
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = instr
    run2._r.append(text)
    run3 = paragraph.add_run()
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run3._r.append(sep)
    if placeholder:
        paragraph.add_run(placeholder)
    run4 = paragraph.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run4._r.append(end)


def add_toc_field(paragraph) -> None:
    add_field(paragraph, r'TOC \o "1-2" \h \z \u', "Right-click and choose Update Field to build the table of contents.")


def add_caption_list_field(paragraph, style_name: str) -> None:
    add_field(paragraph, f'TOC \\h \\z \\t "{style_name},1"',
              "Right-click and choose Update Field to build this list.")


def style_document(doc: Document) -> None:
    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")

    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        st = styles[name]
        st.font.name = "Arial"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        st.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.keep_with_next = True

    title = styles["Title"]
    title.font.name = "Arial"
    title.font.size = Pt(22)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    fig = styles.add_style("Figure Caption", 1)
    fig.base_style = styles["Caption"]
    fig.font.name = "Arial"
    fig.font.size = Pt(9)
    fig.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    fig.paragraph_format.space_before = Pt(4)
    fig.paragraph_format.space_after = Pt(12)
    fig.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fig.paragraph_format.keep_together = True

    tab = styles.add_style("Table Caption", 1)
    tab.base_style = styles["Caption"]
    tab.font.name = "Arial"
    tab.font.size = Pt(9)
    tab.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    tab.paragraph_format.space_before = Pt(10)
    tab.paragraph_format.space_after = Pt(4)
    tab.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    tab.paragraph_format.keep_together = True

    ref = styles.add_style("Reference Entry", 1)
    ref.base_style = styles["Normal"]
    ref.font.size = Pt(9.5)
    ref.paragraph_format.left_indent = Cm(1.0)
    ref.paragraph_format.first_line_indent = Cm(-1.0)
    ref.paragraph_format.space_after = Pt(4)


def setup_page(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    for attr in ("left_margin", "right_margin"):
        setattr(section, attr, Cm(2.5))
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.2)
    section.different_first_page_header_footer = True

    header = section.header
    hp = header.paragraphs[0]
    hp.text = SHORT_TITLE
    hp.style = doc.styles["Normal"]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in hp.runs:
        run.font.size = Pt(8.5)
        run.font.name = "Arial"
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    pf = hp.paragraph_format
    pf.space_after = Pt(0)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(0)
    fp.add_run("Page ")
    add_field(fp, "PAGE", "1")
    fp.add_run(" of ")
    add_field(fp, "NUMPAGES", "1")
    for run in fp.runs:
        run.font.size = Pt(9)
        run.font.name = "Arial"


def add_inline(paragraph, text: str) -> None:
    pos = 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        token = m.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        else:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def add_pipe_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    width = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=width)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        row = row + [""] * (width - len(row))
        for j, value in enumerate(row):
            cell = cells[j]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.space_before = Pt(2)
            add_inline(paragraph, value)
            for run in paragraph.runs:
                run.font.size = Pt(8.5)
                if i == 0:
                    run.bold = True
            if i == 0:
                set_cell_shading(cell, "E8EDF2")
    # repeat header row across pages
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    spacer.paragraph_format.space_before = Pt(0)


def split_pipe(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def build() -> None:
    doc = Document()
    style_document(doc)
    setup_page(doc)
    core = doc.core_properties
    core.title = TITLE
    core.author = "metadore"
    core.last_modified_by = "metadore"
    core.subject = "Connectome-based neural simulation and game control"
    core.keywords = ("connectome; Drosophila; spiking neural network; "
                     "leaky integrate-and-fire; BANC; FlyWire; negative results")
    core.comments = "FLY-SURFER research paper, version 1.1"
    core.category = "Research paper"
    core.created = datetime(2026, 11, 24, 9, 0, 0)
    core.modified = datetime(2026, 11, 24, 9, 0, 0)
    core.revision = 1

    files = sorted(SRC.glob("*.md"))
    title_done = False

    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i]
            line = raw.rstrip()
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            if stripped == "<!-- pagebreak -->":
                doc.add_page_break()
                i += 1
                continue

            if stripped == "[[TOC]]":
                add_toc_field(doc.add_paragraph())
                i += 1
                continue
            if stripped == "[[LOF]]":
                add_caption_list_field(doc.add_paragraph(), "Figure Caption")
                i += 1
                continue
            if stripped == "[[LOT]]":
                add_caption_list_field(doc.add_paragraph(), "Table Caption")
                i += 1
                continue

            m = FIGURE_RE.match(stripped)
            if m:
                number, caption, rel = m.groups()
                image_path = PAPER / rel
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.keep_with_next = True
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(4)
                p.add_run().add_picture(str(image_path), width=Cm(15.6))
                cap = doc.add_paragraph(style="Figure Caption")
                add_inline(cap, f"Figure {number}. {caption}")
                i += 1
                continue

            m = TABLE_CAP_RE.match(stripped)
            if m:
                cap = doc.add_paragraph(style="Table Caption")
                cap.paragraph_format.keep_with_next = True
                add_inline(cap, f"{m.group(1)}. {m.group(2)}")
                i += 1
                continue

            if stripped.startswith("|"):
                block = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    if not PIPETABLE_SEP.match(lines[i].strip()):
                        block.append(split_pipe(lines[i]))
                    i += 1
                add_pipe_table(doc, block)
                continue

            m = HEADING_RE.match(stripped)
            if m:
                level, text = len(m.group(1)), m.group(2).strip()
                if not title_done and level == 1:
                    doc.add_paragraph(text, style="Title")
                    title_done = True
                elif level == 1 or text in FRONT_HEADINGS:
                    doc.add_heading(text, level=1)
                else:
                    doc.add_heading(text, level=2 if level == 2 else 3)
                i += 1
                continue

            if stripped.startswith("**Keywords:**"):
                p = doc.add_paragraph()
                add_inline(p, stripped)
                i += 1
                continue

            if re.match(r"^\[\d+\] ", stripped):
                p = doc.add_paragraph(style="Reference Entry")
                add_inline(p, stripped)
                i += 1
                continue

            m = BULLET_RE.match(stripped)
            if m:
                p = doc.add_paragraph(style="List Bullet")
                add_inline(p, m.group(1))
                i += 1
                continue

            m = NUMBERED_RE.match(stripped)
            if m and len(stripped) < 400:
                p = doc.add_paragraph(style="List Number")
                add_inline(p, m.group(2))
                i += 1
                continue

            p = doc.add_paragraph()
            if EQUATION_TAIL.search(stripped):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_inline(p, stripped)
            i += 1

    doc.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
