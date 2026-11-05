"""Write the broken-down user stories to a PDF: title, description, acceptance criteria.

Usage: python stories_pdf.py stories.json output.pdf
Needs PyMuPDF (pip install pymupdf).

stories.json:
{"document": "name of the spec", "stories": [
  {"title": "...", "description": "Como ..., quero ..., para ...",
   "acceptance_criteria": ["Cenário: ...\n  Dado ...\n  Quando ...\n  Então ...", "..."]}]}
"""
import html
import json
import sys
from pathlib import Path

import fitz

_FIELDS = ("title", "description", "acceptance_criteria")
_CSS = """
body { font-family: sans-serif; font-size: 10pt; }
h1 { font-size: 16pt; margin-bottom: 14pt; }
h2 { font-size: 12pt; margin-top: 18pt; margin-bottom: 4pt; }
.label { font-weight: bold; color: #444444; margin-top: 8pt; margin-bottom: 2pt; }
.criterion { margin-bottom: 6pt; margin-left: 10pt; }
"""


def _text(value: str) -> str:
    return html.escape(value).replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;")


def _validate(data: dict) -> None:
    for number, story in enumerate(data["stories"], 1):
        for field in _FIELDS:
            if not story.get(field):
                raise ValueError(f"story {number} is missing {field}")


def build_html(data: dict) -> str:
    parts = [f"<h1>{_text(data['document'])}</h1>"]
    for number, story in enumerate(data["stories"], 1):
        parts.append(f"<h2>História {number}</h2>")
        parts.append(f"<p class='label'>Título</p><p>{_text(story['title'])}</p>")
        parts.append(f"<p class='label'>Descrição</p><p>{_text(story['description'])}</p>")
        parts.append("<p class='label'>Critérios de aceite</p>")
        parts.extend(f"<p class='criterion'>{_text(c)}</p>" for c in story["acceptance_criteria"])
    return "<body>" + "".join(parts) + "</body>"


def write_pdf(data: dict, out: Path) -> None:
    _validate(data)
    story = fitz.Story(html=build_html(data), user_css=_CSS)
    writer = fitz.DocumentWriter(str(out))
    page = fitz.paper_rect("a4")
    area = page + (48, 48, -48, -48)
    more = True
    while more:
        device = writer.begin_page(page)
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
    writer.close()


if __name__ == "__main__":
    write_pdf(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), Path(sys.argv[2]))
    print(f"PDF written to {sys.argv[2]}")
