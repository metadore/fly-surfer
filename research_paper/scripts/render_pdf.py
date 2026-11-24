"""Update Word fields and export the DOCX as PDF.

Opens the generated DOCX through Word automation, refreshes the table of
contents, the list of figures, the list of tables, and the page-number fields,
saves the DOCX in place, and exports a PDF beside it.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import win32com.client
from pypdf import PdfReader, PdfWriter

PAPER = Path(__file__).resolve().parents[1]
DOCX = PAPER / "FLY_SURFER_COMPLETE_RESEARCH_PAPER.docx"
PDF = PAPER / "FLY_SURFER_COMPLETE_RESEARCH_PAPER.pdf"

TITLE = ("Teaching a Fruit Fly Brain to Play Subway Surfers Through "
         "Connectome-Based Neural Simulation")
SUBJECT = "Connectome-based neural simulation and game control"
KEYWORDS = ("connectome; Drosophila; spiking neural network; "
            "leaky integrate-and-fire; BANC; FlyWire; negative results")
AUTHOR = "metadore"
STAMP = "2026-11-24T09:00:00Z"
PDF_STAMP = "D:20261124090000+00'00'"

WD_STAT_PAGES = 2
WD_EXPORT_PDF = 17


def rewrite_core_properties() -> None:
    """Word stamps lastModifiedBy with the Office user name on save; replace it."""
    tmp = DOCX.with_name(DOCX.name + ".tmp")
    with zipfile.ZipFile(DOCX) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "docProps/core.xml":
                text = data.decode("utf-8")
                text = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>",
                              f"<cp:lastModifiedBy>{AUTHOR}</cp:lastModifiedBy>", text)
                text = re.sub(r"<cp:revision>\d+</cp:revision>",
                              "<cp:revision>1</cp:revision>", text)
                text = re.sub(r"(<dcterms:modified[^>]*>).*?(</dcterms:modified>)",
                              rf"\g<1>{STAMP}\g<2>", text)
                data = text.encode("utf-8")
            dst.writestr(item, data)
    tmp.replace(DOCX)


def rewrite_pdf_metadata() -> None:
    reader = PdfReader(PDF)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    merged = {k: v for k, v in (reader.metadata or {}).items() if v is not None}
    merged.update({
        "/Title": TITLE,
        "/Author": AUTHOR,
        "/Subject": SUBJECT,
        "/Keywords": KEYWORDS,
        "/CreationDate": PDF_STAMP,
        "/ModDate": PDF_STAMP,
    })
    writer.add_metadata(merged)
    tmp = PDF.with_name(PDF.name + ".tmp")
    with open(tmp, "wb") as handle:
        writer.write(handle)
    tmp.replace(PDF)


def main() -> None:
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = word.Documents.Open(str(DOCX), ReadOnly=False)
    try:
        doc.Fields.Update()
        for index in range(1, doc.TablesOfContents.Count + 1):
            doc.TablesOfContents(index).Update()
        for index in range(1, doc.TablesOfFigures.Count + 1):
            doc.TablesOfFigures(index).Update()
        word.ActiveDocument.Repaginate()
        pages = int(doc.ComputeStatistics(WD_STAT_PAGES))
        words = int(doc.ComputeStatistics(0))
        doc.Save()
        doc.ExportAsFixedFormat(str(PDF), WD_EXPORT_PDF)
        print(f"pages={pages} words={words}")
        print(f"toc={doc.TablesOfContents.Count} lof={doc.TablesOfFigures.Count}")
    finally:
        doc.Close(SaveChanges=True)
        word.Quit()

    rewrite_core_properties()
    rewrite_pdf_metadata()


if __name__ == "__main__":
    main()
