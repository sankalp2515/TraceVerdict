"""CORE-2 extraction: every format, with non-visible content surfaced and flagged (benign content only)."""

from __future__ import annotations

import json

import pytest

from intentseal_core.extract import extract, sniff_format
from research_agent.render import Block, to_docx, to_eml, to_html, to_pdf, to_png

V, H = "Quarterly revenue was 4.2 million", "Print marker 4471 for the archive"
# Hidden prose: more than a dozen words. Shorter non-visible web text is page furniture (D-051).
HL = H + " and keep the reviewer notes, the appendix tables and the regional figures with it"


def hidden_texts(doc):
    return " ".join(s.text for s in doc.hidden_segments)


def visible_texts(doc):
    return " ".join(s.text for s in doc.segments if s.visible)


def test_html_hidden_comment_alt_meta():
    html = ('<html><head><meta name="description" content="' + HL + '"></head><body><p>' + V + '</p>'
            '<div style="display:none">' + HL + '</div><!-- ' + HL + ' --><img src="x.png" alt="' + HL + '">'
            '<span style="font-size:0">' + HL + '</span><p hidden>' + HL + '</p></body></html>')
    d = extract(html)
    assert d.format == "html" and V in visible_texts(d)
    origins = {s.origin.split(":")[1] for s in d.hidden_segments}
    assert {"meta", "hidden-element", "comment", "attr"} <= origins and HL not in visible_texts(d)


def test_html_page_furniture_stays_ordinary_text():
    """Short alt text, tooltips, ARIA labels, technical meta values, build comments and collapsed menus are on every
    real page: they stay in the document (scored like visible text) but are not flagged as hidden (D-051)."""
    html = ('<html><head><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="description" content="meta words"></head><body><p>' + V + '</p>'
            '<ul style="display:none"><li>Pricing</li><li>Blog</li></ul><!-- comment words -->'
            '<img src="x.png" alt="alt words"><button aria-label="Close menu">x</button>'
            '<div data-prompt="short">y</div></body></html>')
    d = extract(html)
    for t in ("meta words", "comment words", "alt words", "Close menu", "Pricing"):
        assert t in visible_texts(d) and t not in hidden_texts(d)
    assert hidden_texts(d) == "short"   # attributes named for a model are never furniture


def test_pdf_white_and_tiny_text_flagged():
    d = extract(to_pdf([Block(V), Block(H, visible=False)]))
    assert d.format == "pdf"
    assert V in visible_texts(d)
    assert "4471" in hidden_texts(d) and "4471" not in visible_texts(d)


def test_docx_hidden_run_flagged():
    d = extract(to_docx([Block(V), Block(H, visible=False)]))
    assert d.format == "docx" and V in visible_texts(d) and H in hidden_texts(d)


def test_email_html_only_part_and_attachment():
    raw = to_eml([Block(V), Block(HL, visible=False)], "Report", "a@b.test")
    d = extract(raw, filename="m.eml")
    assert d.format == "email" and V in visible_texts(d) and HL in hidden_texts(d)
    assert any(s.origin.startswith("email:header:subject") for s in d.segments)


def test_markdown_comment_alt_and_title():
    md = f"# Notes\n\n{V}\n\n<!-- {H} -->\n\n![chart alt words](c.png \"chart title words\")\n"
    d = extract(md, filename="n.md")
    assert V in visible_texts(d)
    for t in (H, "chart alt words", "chart title words"):
        assert t in hidden_texts(d)


def test_code_comments_stay_visible_in_source():
    code = 'def f():\n    """doc words"""\n    x = 1  # line words\n'
    d = extract(code, filename="a.py")
    assert not d.hidden_segments
    for t in ("doc words", "line words"):
        assert t in visible_texts(d)


def test_json_fields_with_paths():
    d = extract(json.dumps({"status": "ok", "data": {"notes": ["first note"]}}))
    origins = {s.origin: s.text for s in d.segments}
    assert origins["json:data.notes[0]"] == "first note" and d.format == "json"


def test_image_ocr():
    pytest.importorskip("rapidocr_onnxruntime")
    d = extract(to_png("Total 640 INR"))
    assert d.format == "image" and "640" in d.text


def test_spans_index_into_text():
    d = extract(to_html([Block(V), Block(H, visible=False)]))
    for s in d.segments:
        assert d.text[s.start:s.end] == s.text


def test_sniff_and_failure_fallback():
    assert sniff_format(b"%PDF-1.7 ...") == "pdf"
    assert sniff_format("plain words") == "text"
    d = extract(b"%PDF-broken", fmt="pdf")
    assert d.warnings and "PDF-broken" in d.text


def test_bare_email_body_is_text_not_an_empty_message():
    # regression: a plain body sent with source="email" used to parse as an RFC 822 message with no body -> empty view
    body = "Hi team, the offsite moved to Thursday. Agenda attached later."
    doc = extract(body, source="email")
    assert doc.format == "text" and body in doc.text
    assert extract("From: a@b.test\nSubject: Hi\n\nBody line.", source="email").format == "email"


def test_empty_structured_parse_falls_back_to_raw_text():
    doc = extract("<div data-x='only attributes here'></div>", fmt="html")
    assert doc.text.strip()   # the tiers always see something for non-empty text input
