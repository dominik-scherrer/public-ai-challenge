import httpx
import pymupdf
import pytest

from public_ai_challenge.phase2_synthesis_gemeinde.extraction import (
    convert_to_markdown,
    extract_html_to_markdown,
    extract_pdf_to_markdown,
    fetch_content,
)


def test_extract_html_to_markdown():
    html = b"""
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title><style>.hidden{display:none;}</style></head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <header><h1>Header to Ignore</h1></header>
        <main>
            <h1>Anmeldung Wohnsitz</h1>
            <p>Herzlich willkommen in Ausserberg. Bitte melden Sie sich innerhalb von 14 Tagen an.</p>
            <ul>
                <li>Heimatschein</li>
                <li>Mietvertrag</li>
            </ul>
        </main>
        <footer><p>Impressum</p></footer>
        <script>console.log("ignore");</script>
    </body>
    </html>
    """
    md = extract_html_to_markdown(html)
    assert "# Anmeldung Wohnsitz" in md
    assert "Herzlich willkommen in Ausserberg" in md
    assert "Heimatschein" in md
    assert "Mietvertrag" in md
    # Stripped elements
    assert "Header to Ignore" not in md
    assert "Home" not in md
    assert "Impressum" not in md
    assert "console.log" not in md


def test_extract_pdf_to_markdown():
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Gemeinde Ausserberg Reglement")
    pdf_bytes = doc.tobytes()
    doc.close()

    md = extract_pdf_to_markdown(pdf_bytes)
    assert "Gemeinde Ausserberg Reglement" in md
    assert "## Page 1" in md


@pytest.mark.anyio
async def test_fetch_content_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html="<h1>Sample</h1>", headers={"content-type": "text/html; charset=utf-8"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        content, ctype = await fetch_content("https://example.com/test", client)
        assert b"Sample" in content
        assert "text/html" in ctype


def test_convert_to_markdown_detection():
    html_sample = b"<h1>Title</h1><p>Body</p>"
    md = convert_to_markdown(html_sample, "text/html")
    assert "# Title" in md
    assert "Body" in md
