"""Typer/Rich commands for municipality discovery and deterministic MCP packaging."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.text import Text

from publicai.config import Settings, load_settings
from publicai.contracts import load_discovery
from publicai.observability import configure

app = typer.Typer(
    no_args_is_help=True, help="Build evidence-backed, read-only municipality MCP servers."
)
console = Console(stderr=True)


def _settings(
    config: Path | None,
    model: str | None,
    discovery_model: str | None,
    review_model: str | None,
) -> Settings:
    load_dotenv()
    settings = load_settings(config)
    if model:
        settings.model.discovery_model = model
        settings.model.review_model = model
    if discovery_model:
        settings.model.discovery_model = discovery_model
    if review_model:
        settings.model.review_model = review_model
    configure(settings.telemetry)
    return settings


def _progress(message: str) -> None:
    console.print(message, style="cyan", markup=False)


def _coverage(path: Path) -> None:
    discovery = load_discovery(path)
    table = Table(title=Text(f"{discovery.identity.name.value} — build-time snapshot"))
    table.add_column("Capability")
    table.add_column("Coverage")
    table.add_column("Entries", justify="right")
    for name, capability in discovery.capabilities.items():
        table.add_row(name, capability.coverage, str(len(capability.entries)))
    console.print(table)
    if any(cap.coverage != "supported" for cap in discovery.capabilities.values()):
        console.print(
            "Partial coverage: see report.md for gaps and official handoffs.", style="yellow"
        )


def _failure(error: Exception) -> None:
    from publicai.agents import ModelConfigurationError
    from publicai.builder import BuildError
    from publicai.crawler import CrawlError
    from publicai.pipeline import DiscoveryError

    if isinstance(error, (BuildError, DiscoveryError)):
        if isinstance(error, DiscoveryError):
            console.print(str(error), style="red", markup=False)
        console.print(f"Failed. Diagnostic: {error.diagnostic_path}", style="red", markup=False)
    elif isinstance(error, (ModelConfigurationError, CrawlError)):
        console.print(str(error), style="red", markup=False)
    else:
        # Do not print SDK/config exception payloads, which can contain credentials.
        console.print(
            f"Failed ({type(error).__name__}). Check configuration and required API key.",
            style="red",
        )
    raise typer.Exit(1) from error


@app.command()
def discover(
    url: str,
    out: Annotated[Path, typer.Option(help="Artifact root; each run creates a unique directory.")],
    config: Annotated[Path | None, typer.Option()] = None,
    model: Annotated[
        str | None, typer.Option(help="Override both configured agent models.")
    ] = None,
    discovery_model: Annotated[
        str | None, typer.Option(help="Discovery model; takes precedence over --model.")
    ] = None,
    review_model: Annotated[
        str | None, typer.Option(help="Evidence-review model; takes precedence over --model.")
    ] = None,
) -> None:
    """Inspect www.ausserberg.ch and retain a reviewed discovery artifact."""
    from publicai.pipeline import discover as discover_pipeline

    try:
        settings = _settings(config, model, discovery_model, review_model)
        path = asyncio.run(discover_pipeline(url, out, settings, _progress))
        _coverage(path)
        console.print(f"Discovery: {path}", markup=False)
    except Exception as error:
        _failure(error)


@app.command()
def build(discovery_json: Path, out: Annotated[Path, typer.Option()]) -> None:
    """Validate and package an existing discovery without model calls or website access."""
    from publicai.builder import build as build_package

    try:
        package = build_package(discovery_json, out)
        _coverage(package / "discovery.json")
        console.print(f"Package: {package}", markup=False)
    except Exception as error:
        _failure(error)


@app.command()
def run(
    url: str,
    out: Annotated[Path, typer.Option()],
    config: Annotated[Path | None, typer.Option()] = None,
    model: Annotated[
        str | None, typer.Option(help="Override both configured agent models.")
    ] = None,
    discovery_model: Annotated[
        str | None, typer.Option(help="Discovery model; takes precedence over --model.")
    ] = None,
    review_model: Annotated[
        str | None, typer.Option(help="Evidence-review model; takes precedence over --model.")
    ] = None,
) -> None:
    """Run discovery, evidence review, deterministic packaging and offline conformance."""
    from publicai.builder import build as build_package
    from publicai.pipeline import discover as discover_pipeline

    try:
        settings = _settings(config, model, discovery_model, review_model)
        path = asyncio.run(discover_pipeline(url, out, settings, _progress))
        _progress("Building the fixed MCP template and running offline conformance")
        package = build_package(path, out)
        _coverage(package / "discovery.json")
        console.print(f"Discovery: {path}\nPackage: {package}", markup=False)
    except Exception as error:
        _failure(error)
