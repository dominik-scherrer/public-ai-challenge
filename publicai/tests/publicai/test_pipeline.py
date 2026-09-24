"""The normal agent workflow publishes only complete, validated reviews."""

import html
import json
from pathlib import Path

import httpx
import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from publicai.agents import Inventory, claim_records, create_agents
from publicai.config import Settings
from publicai.crawler import FetchedPage, Link, SafeCrawler
from publicai.pipeline import DiscoveryError, discover_with_agents

FIXTURE = Path(__file__).parents[2] / "src/publicai/fixtures/representative.json"


async def test_optional_empty_contact_page_does_not_abort_discovery(tmp_path: Path) -> None:
    agents, retained = fixture_agents(Settings())
    sources = {source["url"]: source for source in retained.sources}

    async def resolver(host: str, port: int) -> list[str]:
        return ["93.184.216.34"]

    def respond(request: httpx.Request) -> httpx.Response:
        source = sources.get(str(request.url))
        if source:
            content = "<p>" + html.escape(source["text"]) + "</p>"
            for url in source["links"]:
                content += f'<a href="{html.escape(url, quote=True)}">fixture</a>'
            content += '<a href="/impressum-empty">Impressum</a>'
            content += '<a href="/fixture-contact">Kontakt</a>'
            return httpx.Response(200, headers={"content-type": "text/html"}, text=content)
        if request.url.path == "/impressum-empty":
            return httpx.Response(
                200, headers={"content-type": "text/html"}, text="<script>render()</script>"
            )
        return httpx.Response(404)

    async with SafeCrawler(resolver=resolver, transport=httpx.MockTransport(respond)) as crawler:
        path = await discover_with_agents(
            "https://www.ausserberg.ch/", tmp_path, Settings(), agents, crawler
        )
    discovery = json.loads(path.read_text())
    assert discovery["review"]["status"] == "passed"
    assert any(failure["reason"] == "inaccessible" for failure in discovery["failures"])


class RetainedCrawler:
    """Network-free acquisition boundary returning independently authored fixture text."""

    request_count = 2
    failures: list = []
    discovered_urls: list[str] = []

    def __init__(self, sources: list[dict]) -> None:
        self.sources = sources

    async def seed(self, url: str) -> list[FetchedPage]:
        assert url == "https://www.ausserberg.ch/"
        return [
            FetchedPage(
                url=s["url"],
                title=s["title"],
                text=s["text"],
                retrieved_at=s["retrieved_at"],
                sha256=s["sha256"],
                links=[Link(url=url, label="fixture", kind="html") for url in s["links"]],
            )
            for s in self.sources
        ]


def fixture_agents(settings: Settings, *, approve: bool = True) -> tuple:
    fixture = json.loads(FIXTURE.read_text())
    # The application assigns source IDs rather than accepting model-generated IDs.
    inventory = {key: fixture[key] for key in ("identity", "capabilities")}
    serialized = (
        json.dumps(inventory)
        .replace('"source_id": "home"', '"source_id": "source-1"')
        .replace('"source_id": "contact"', '"source_id": "source-2"')
    )
    inventory = Inventory.model_validate_json(serialized).model_dump(mode="json")
    claims = claim_records(inventory)

    def extract(messages: object, info: object) -> ModelResponse:
        assert {tool.name for tool in info.function_tools} == {"web_fetch", "list_sources"}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, inventory)])

    def review(messages: object, info: object) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "identity_consistent": True,
                        "checks": [
                            {"path": path, "status": "supported", "reason": "Fixture evidence"}
                            for path in claims
                        ]
                        if approve
                        else [],
                        "issues": [],
                    },
                )
            ]
        )

    return create_agents(settings, FunctionModel(extract), FunctionModel(review)), RetainedCrawler(
        fixture["sources"]
    )


async def test_complete_pipeline_runs_agents_and_publishes_unique_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    settings = Settings()
    agents, crawler = fixture_agents(settings)
    first = await discover_with_agents(
        "https://www.ausserberg.ch/", tmp_path, settings, agents, crawler
    )
    agents, crawler = fixture_agents(settings)
    second = await discover_with_agents(
        "https://www.ausserberg.ch/", tmp_path, settings, agents, crawler
    )
    assert first != second
    assert first.is_file() and second.is_file()
    assert json.loads(first.read_text())["review"]["status"] == "passed"
    assert len(json.loads((first.parent / "review.json").read_text())["checks"]) > 10
    assert not list(tmp_path.glob(".staging-*"))


async def test_incomplete_semantic_review_never_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    agents, crawler = fixture_agents(Settings(), approve=False)
    with pytest.raises(DiscoveryError) as error:
        await discover_with_agents(
            "https://www.ausserberg.ch/", tmp_path, Settings(), agents, crawler
        )
    assert error.value.diagnostic_path.is_file()
    diagnostic = json.loads(error.value.diagnostic_path.read_text())
    assert diagnostic["message"] == "Semantic review must check every claim exactly once."
    assert str(error.value) == diagnostic["message"]
    assert not list(tmp_path.glob("discovery-*"))
    assert not list(tmp_path.glob(".staging-*"))


def test_minimization_removes_uncited_text_and_links() -> None:
    from publicai.contracts import load_discovery
    from publicai.pipeline import minimize_sources

    discovery = load_discovery(FIXTURE)
    minimized = minimize_sources(discovery)
    assert all("FICTIONAL TEST FIXTURE" not in source.text for source in minimized.sources)
    assert all(
        source.links == ["https://portal.example.test/registration"] or source.links == []
        for source in minimized.sources
    )
    assert minimized.identity == discovery.identity
    assert minimized.capabilities == discovery.capabilities


async def test_provider_error_payload_is_not_exposed(tmp_path: Path) -> None:
    agents, crawler = fixture_agents(Settings())

    def fail(messages: object, info: object) -> ModelResponse:
        raise ValueError("private-provider-payload")

    with agents.reviewer.override(model=FunctionModel(fail)):
        with pytest.raises(DiscoveryError) as error:
            await discover_with_agents(
                "https://www.ausserberg.ch/", tmp_path, Settings(), agents, crawler
            )
    assert "private-provider-payload" not in str(error.value)
    assert "private-provider-payload" not in error.value.diagnostic_path.read_text()
    assert not list(tmp_path.glob("discovery-*"))


def test_minimization_preserves_uninspected_document_evidence() -> None:
    import hashlib

    from publicai.builder import render_report
    from publicai.contracts import Discovery, EvidenceRef, Fact, LinkedDocument, load_discovery
    from publicai.pipeline import minimize_sources

    discovery = load_discovery(FIXTURE)
    source = discovery.sources[1]
    url = "https://www.ausserberg.ch/calendar.pdf"
    excerpt = f"Fixture calendar: {url}"
    evidence = [EvidenceRef(source_id=source.id, excerpt=excerpt)]
    document = LinkedDocument(
        title=Fact(value="Fixture calendar", evidence=evidence),
        url=Fact(value=url, evidence=evidence),
        kind="pdf",
    )
    text = source.text + "\n" + excerpt
    discovery.sources[1] = source.model_copy(
        update={
            "documents": [document],
            "links": [*source.links, url],
            "text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
    )
    discovery = Discovery.model_validate(discovery.model_dump())
    minimized = minimize_sources(discovery)
    assert minimized.sources[1].documents[0].status == "uninspected"
    assert excerpt in minimized.sources[1].text
    assert url in minimized.sources[1].links
    report = render_report(minimized)
    assert "Uninspected document links" in report
    assert "document contents are unknown" in report
    assert url in report
