"""The adapted crawler stays locked to exactly one host (now a parameter)."""

import httpx
import pytest

from mmp.build.crawler import CrawlError, SafeCrawler, validate_url

HOST = "www.wettingen.ch"
PAGES = {
    "/robots.txt": ("text/plain", "User-agent: *\nDisallow: /intern/\n"),
    "/": ("text/html", '<html><head><title>Wettingen</title></head><body><main><a href="/dienstleistungen/6348">Anmeldung / Zuzug</a>'
          '<a href="https://evil.example/x">x</a><a href="/intern/geheim">intern</a></main></body></html>'),
    "/sitemap.xml": ("application/xml", "<urlset></urlset>"),
    "/dienstleistungen/6348": ("text/html", "<html><body><main><h1>Anmeldung / Zuzug</h1><p>Bitte nehmen Sie die Anmeldung innert 14 Tagen ab Einzugsdatum vor.</p></main></body></html>"),
}


def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.host == HOST, "crawler must never leave the authorized host"
    if request.url.path not in PAGES:
        return httpx.Response(404)
    ctype, body = PAGES[request.url.path]
    return httpx.Response(200, headers={"content-type": ctype}, content=body.encode())


async def fake_resolver(host, port):
    return ["203.0.113.10"] if False else ["8.8.8.8"]


def test_validate_url_is_host_bound():
    assert validate_url("https://www.wettingen.ch/a", HOST) == "https://www.wettingen.ch/a"
    with pytest.raises(CrawlError):
        validate_url("https://www.duebendorf.ch/a", HOST)
    with pytest.raises(CrawlError):
        validate_url("https://www.wettingen.ch/a?session=1", HOST)


async def test_crawl_follows_service_links_only_on_host():
    async with SafeCrawler(HOST, resolver=fake_resolver, transport=httpx.MockTransport(handler)) as crawler:
        pages = await crawler.crawl("https://www.wettingen.ch/", max_pages=10)
    urls = {p.url for p in pages}
    assert "https://www.wettingen.ch/dienstleistungen/6348" in urls
    assert not any("evil" in u or "intern" in u for u in urls)
    zuzug = next(p for p in pages if p.url.endswith("6348"))
    assert "innert 14 Tagen" in zuzug.text
