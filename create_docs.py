#!/usr/bin/env python3
"""
Jarvis - create a Word file or a PDF from what you say.
Commands:
    create word <title> : <text>
    make pdf <title> : <text>
    create word my resume notes : Python, SQL, Power BI in progress
Files are saved in the jarvis folder, named from the title + date.
Needs: python-docx (Word) and fpdf2 (PDF) - both in requirements.txt.
"""
import datetime
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def _safe_name(title):
    name = re.sub(r"[^A-Za-z0-9 _-]+", "", title).strip().replace(" ", "-").lower()
    return name or "jarvis-document"


def _stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def make_word(title, text):
    try:
        import docx
    except ImportError:
        return "", "Word support needs python-docx. Run: pip install -r requirements.txt"
    filename = os.path.join(HERE, f"{_safe_name(title)}-{_stamp()}.docx")
    doc = docx.Document()
    doc.add_heading(title, level=1)
    for para in text.split("\n"):
        para = para.strip()
        if para:
            doc.add_paragraph(para)
    doc.save(filename)
    return filename, ""


def make_pdf(title, text):
    try:
        from fpdf import FPDF
    except ImportError:
        return "", "PDF support needs fpdf2. Run: pip install -r requirements.txt"
    filename = os.path.join(HERE, f"{_safe_name(title)}-{_stamp()}.pdf")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 12, title)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    for para in text.split("\n"):
        para = para.strip()
        if para:
            pdf.multi_cell(0, 7, para)
            pdf.ln(2)
    pdf.output(filename)
    return filename, ""


if __name__ == "__main__":
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else "pdf"
    title = sys.argv[2] if len(sys.argv) > 2 else "Test document"
    text = " ".join(sys.argv[3:]) or "This is a test document made by Jarvis."
    fn, err = make_word(title, text) if kind == "word" else make_pdf(title, text)
    print(err or f"Saved to: {fn}")
