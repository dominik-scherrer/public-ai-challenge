"""Evidence-backed municipality MCP server factory."""


def main() -> None:
    """Launch the Typer factory application."""
    from public_ai_challenge.alternative_pipeline_publicai.cli import app

    app()
