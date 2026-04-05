#!/usr/bin/env python3
"""Convert markdown paper draft to PDF via WeasyPrint."""
import markdown
from weasyprint import HTML
from pathlib import Path

ROOT = Path(__file__).parent

md_text = (ROOT / "draft_v1.md").read_text(encoding="utf-8")

html_body = markdown.markdown(md_text, extensions=["tables", "smarty"])

html_full = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: A4;
    margin: 25mm 20mm 25mm 20mm;
    @bottom-center {{
        content: counter(page);
        font-size: 9pt;
        color: #666;
    }}
}}
body {{
    font-family: 'Georgia', 'Times New Roman', serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
    max-width: 100%;
}}
h1 {{
    font-size: 16pt;
    line-height: 1.3;
    margin-bottom: 6pt;
    text-align: center;
}}
h2 {{
    font-size: 13pt;
    margin-top: 24pt;
    margin-bottom: 8pt;
    border-bottom: 1px solid #ccc;
    padding-bottom: 4pt;
}}
h3 {{
    font-size: 11.5pt;
    margin-top: 18pt;
    margin-bottom: 6pt;
}}
p {{
    margin-bottom: 8pt;
    text-align: justify;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 12pt 0;
    font-size: 9.5pt;
}}
th, td {{
    border: 1px solid #ccc;
    padding: 4pt 6pt;
    text-align: left;
}}
th {{
    background: #f0f0f0;
    font-weight: 600;
}}
td:first-child {{
    font-weight: 500;
}}
strong {{
    font-weight: 600;
}}
em {{
    font-style: italic;
}}
hr {{
    border: none;
    border-top: 1px solid #ccc;
    margin: 20pt 0;
}}
ol, ul {{
    margin-bottom: 8pt;
    padding-left: 24pt;
}}
li {{
    margin-bottom: 4pt;
}}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

out_path = ROOT / "draft_v1.pdf"
HTML(string=html_full).write_pdf(str(out_path))
print(f"PDF written to {out_path}")
