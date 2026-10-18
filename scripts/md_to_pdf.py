"""Markdown to PDF converter using ReportLab.
Converts standard GitHub Flavored Markdown (headings, tables, lists, code blocks, alerts)
into clean, well-formatted printable PDF documents.
"""

import os
import re
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)


def md_to_pdf(md_path: str, pdf_path: str, title: str = "LandGuard Document"):
    """Converts a Markdown file into a printable PDF."""
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Define custom styles
    h1_style = ParagraphStyle(
        "MD_H1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=8,
        spaceBefore=14,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "MD_H2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
        spaceBefore=12,
        keepWithNext=True,
    )
    h3_style = ParagraphStyle(
        "MD_H3",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
        spaceBefore=8,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "MD_Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "MD_Bullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E293B"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )
    code_style = ParagraphStyle(
        "MD_Code",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )
    table_cell_style = ParagraphStyle(
        "MD_TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )
    table_header_style = ParagraphStyle(
        "MD_TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )
    callout_style = ParagraphStyle(
        "MD_Callout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.0,
        leading=11.0,
        textColor=colors.HexColor("#0F766E"),
        leftIndent=12,
        spaceAfter=5,
    )

    def clean_inline(text: str) -> str:
        """Translates inline markdown formatting to ReportLab XML tags safely."""
        # 1. Extract inline code blocks first
        code_tokens = []
        def code_sub(m):
            idx = len(code_tokens)
            code_tokens.append(m.group(1))
            return f"__INLINE_CODE_{idx}__"

        text = re.sub(r"`([^`]+)`", code_sub, text)

        # 2. Escape XML entities
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 3. Bold (**bold**)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)

        # 4. Italic (*italic* only, avoid underscore to preserve snake_case identifiers)
        text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

        # 5. Restore code tokens
        for idx, raw_code in enumerate(code_tokens):
            esc = raw_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            token = f"__INLINE_CODE_{idx}__"
            text = text.replace(token, f'<font face="Courier" color="#0369A1">{esc}</font>')

        return text

    story = []
    lines = md_text.splitlines()
    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                # Close code block
                code_text = "<br/>".join(
                    l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
                    for l in code_lines
                )
                p = Paragraph(code_text, code_style)
                t = Table([[p]], colWidths=[540])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 6))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___") or re.match(r"^[-*_]{3,}$", stripped):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=6, spaceBefore=4))
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            story.append(Paragraph(clean_inline(stripped[2:]), h1_style))
            i += 1
            continue
        elif stripped.startswith("## "):
            story.append(Paragraph(clean_inline(stripped[3:]), h2_style))
            i += 1
            continue
        elif stripped.startswith("### "):
            story.append(Paragraph(clean_inline(stripped[4:]), h3_style))
            i += 1
            continue
        elif stripped.startswith("#### "):
            story.append(Paragraph(clean_inline(stripped[5:]), h3_style))
            i += 1
            continue

        # Blockquote / Callout
        if stripped.startswith(">"):
            callout_text = clean_inline(stripped.lstrip("> ").strip())
            story.append(Paragraph(callout_text, callout_style))
            i += 1
            continue

        # Markdown Table
        if stripped.startswith("|") and stripped.endswith("|"):
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                row_line = lines[i].strip()
                # Check if it's separator row |---|---|
                if re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", row_line):
                    i += 1
                    continue
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                table_rows.append(cells)
                i += 1

            if table_rows:
                # Determine max columns
                max_cols = max(len(r) for r in table_rows)
                # Pad uneven rows
                for r in table_rows:
                    while len(r) < max_cols:
                        r.append("")

                col_w = 540 / max_cols if max_cols > 0 else 540
                col_widths = [col_w] * max_cols

                # Refine column widths if specific column count
                if max_cols == 2:
                    col_widths = [160, 380]
                elif max_cols == 3:
                    col_widths = [110, 150, 280]
                elif max_cols == 4:
                    col_widths = [80, 100, 160, 200]
                elif max_cols == 5:
                    col_widths = [65, 85, 110, 120, 160]
                elif max_cols == 6:
                    col_widths = [55, 75, 90, 100, 100, 120]
                elif max_cols == 7:
                    col_widths = [45, 65, 75, 80, 85, 90, 100]

                table_data = []
                for row_idx, r in enumerate(table_rows):
                    row_cells = []
                    for c in r:
                        st = table_header_style if row_idx == 0 else table_cell_style
                        row_cells.append(Paragraph(clean_inline(c), st))
                    table_data.append(row_cells)

                t = Table(table_data, colWidths=col_widths, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(t)
                story.append(Spacer(1, 6))
            continue

        # Bullet list
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_text = "&bull; " + clean_inline(stripped[2:])
            story.append(Paragraph(bullet_text, bullet_style))
            i += 1
            continue

        # Numbered list
        m_num = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m_num:
            num_text = f"<b>{m_num.group(1)}.</b> " + clean_inline(m_num.group(2))
            story.append(Paragraph(num_text, bullet_style))
            i += 1
            continue

        # Regular text paragraph
        story.append(Paragraph(clean_inline(stripped), body_style))
        i += 1

    doc.build(story)
    print(f"Generated PDF: {pdf_path}")
