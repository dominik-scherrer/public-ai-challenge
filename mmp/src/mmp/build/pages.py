"""Retained public pages — the only ground truth a Build may quote from.

Two ways a page gets here, recorded per Source as ``capture_method``:

- ``crawler``: :class:`mmp.build.crawler.SafeCrawler` fetched it (the normal Build).
- ``browser_capture``: the page's visible text was captured in a browser and
  saved under ``data/captures/<slug>/*.txt``. Used where the crawler cannot run
  (network-restricted build hosts, or sites whose bot protection times out
  non-browser clients). The capture format is a small header plus the text::

      url: https://www.wettingen.ch/dienstleistungen/6348
      title: Wettingen - Anmeldung / Zuzug
      retrieved_at: 2026-09-24T20:12:08Z
      link: eUmzug | https://ag.eumzug.swiss/
      ---
      <page text>
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class PageLink:
    label: str
    url: str


@dataclass
class Page:
    id: str
    url: str
    title: str
    text: str
    retrieved_at: datetime
    capture_method: str
    links: list[PageLink] = field(default_factory=list)

    @property
    def sha256(self) -> str:
        return sha256(self.text.encode()).hexdigest()


def load_capture_file(path: Path) -> Page:
    raw = path.read_text(encoding="utf-8")
    header, sep, body = raw.partition("\n---\n")
    if not sep:
        raise ValueError(f"{path}: capture file needs a '---' line between header and text")
    meta: dict[str, str] = {}
    links: list[PageLink] = []
    for line in header.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "link":
            label, _, url = value.partition("|")
            links.append(PageLink(label=label.strip(), url=url.strip()))
        else:
            meta[key] = value
    for required in ("url", "retrieved_at"):
        if required not in meta:
            raise ValueError(f"{path}: missing '{required}' in capture header")
    retrieved = datetime.fromisoformat(meta["retrieved_at"].replace("Z", "+00:00"))
    return Page(
        id=path.stem,
        url=meta["url"],
        title=meta.get("title", ""),
        text=body.strip(),
        retrieved_at=retrieved,
        capture_method="browser_capture",
        links=links,
    )


def load_capture_dir(directory: Path) -> list[Page]:
    pages = [load_capture_file(p) for p in sorted(directory.glob("*.txt"))]
    if not pages:
        raise ValueError(f"No capture files (*.txt) in {directory}")
    return pages


def pages_from_crawl(fetched: list) -> list[Page]:
    """Convert crawler ``FetchedPage`` objects into Pages with stable ids."""
    pages: list[Page] = []
    for i, fp in enumerate(fetched):
        pages.append(
            Page(
                id=f"p{i:03d}",
                url=fp.url,
                title=fp.title,
                text=fp.text,
                retrieved_at=fp.retrieved_at if fp.retrieved_at.tzinfo else fp.retrieved_at.replace(tzinfo=UTC),
                capture_method="crawler",
                links=[PageLink(label=link.label, url=link.url) for link in fp.links],
            )
        )
    return pages
