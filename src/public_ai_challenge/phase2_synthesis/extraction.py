"""Content extraction module for HTML and PDF fetching and conversion."""

from __future__ import annotations

import logging
from typing import Tuple

from bs4 import BeautifulSoup
import httpx
import markdownify
import pymupdf

logger = logging.getLogger(__name__)


# [C_GMP_03_01] [SP_GMP_02_01] fetch_content
async def fetch_content(url: str, client: httpx.AsyncClient) -> Tuple[bytes, str]:
    """Fetch content from a URL asynchronously and return bytes and content type.

    Raises:
        httpx.HTTPError: If the HTTP request fails.
    """
    response = await client.get(url, follow_redirects=True, timeout=15.0)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    return response.content, content_type


# [C_GMP_03_01] [SP_GMP_02_01] extract_html_to_markdown
def extract_html_to_markdown(html_bytes: bytes) -> str:
    """Parse HTML and convert primary content to Markdown."""
    soup = BeautifulSoup(html_bytes, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()

    # Prefer <main>, <article>, or fall back to <body>
    main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup
    html_str = str(main_content)

    md = markdownify.markdownify(html_str, heading_style="ATX", strip=["script", "style"])
    # Clean up excessive newlines
    lines = [line.strip() for line in md.splitlines()]
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
                prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    return "\n".join(cleaned).strip()


# [C_GMP_03_01] [SP_GMP_02_01] extract_pdf_to_markdown
def extract_pdf_to_markdown(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes and convert to basic Markdown."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages_text: list[str] = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text").strip()
        if text:
            pages_text.append(f"## Page {page_num + 1}\n\n{text}")

    doc.close()
    return "\n\n".join(pages_text).strip()


# [C_GMP_03_01] [SP_GMP_02_01] convert_to_markdown
def convert_to_markdown(content: bytes, content_type: str) -> str:
    """Detect content type and convert content bytes to Markdown."""
    if "application/pdf" in content_type or content.startswith(b"%PDF-"):
        return extract_pdf_to_markdown(content)
    return extract_html_to_markdown(content)
