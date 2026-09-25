"""Immutable publication and evidence boundaries for generated MCP packages."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from publicai.builder import BuildError, _run_conformance, build, render_report
from publicai.contracts import load_discovery

FIXTURE = Path(__file__).parents[2] / "src" / "publicai" / "fixtures" / "representative.json"


def test_invalid_discovery_produces_only_diagnostic(tmp_path: Path) -> None:
    """Invalid input must not leave an apparent release package."""
    discovery = tmp_path / "invalid.json"
    discovery.write_text('{"contract_version": "unsupported"}', encoding="utf-8")
    output = tmp_path / "artifacts"

    with pytest.raises(BuildError, match="validation") as error:
        build(discovery, output)

    assert error.value.diagnostic_path.is_file()
    assert list(output.glob("build-*")) == []
    assert list(output.glob(".staging-*")) == []
    assert "failed" in error.value.diagnostic_path.read_text(encoding="utf-8").lower()


def test_rebuilding_is_immutable_and_manifest_covers_every_file(tmp_path: Path) -> None:
    """Same discovery produces distinct releases without overwriting any bytes."""
    first = build(FIXTURE, tmp_path)
    original = {
        path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()
    }
    second = build(FIXTURE, tmp_path)

    assert first != second
    for package in (first, second):
        service = yaml.safe_load((package / "compose.yaml").read_text())["services"]["municipality"]
        assert "image" not in service  # Compose derives an image from the unique project name.
        assert service["build"] == "."
        assert '"--health-check"' in (package / "Dockerfile").read_text()
    assert original == {
        path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()
    }
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_id"] != manifest["discovery_id"]
    assert manifest["build_id"] == first.name
    assert set(manifest["files"]) == {
        path.as_posix() for path in original if path.as_posix() != "manifest.json"
    }
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == expected
    assert list(tmp_path.glob(".staging-*")) == []
    assert {
        "pyproject.toml",
        "uv.lock",
        "Dockerfile",
        "compose.yaml",
        "README.md",
        "llms.txt",
        "municipality.md",
        "report.md",
        "discovery.json",
        "src",
        "tests",
        "fixtures",
    } <= {path.name for path in first.iterdir()}


@pytest.mark.parametrize("invalidity", ["version", "identity", "evidence", "review", "capability"])
def test_untrusted_discovery_must_pass_all_publication_gates(
    tmp_path: Path, invalidity: str
) -> None:
    """A candidate cannot bypass version, identity, citations, review or catalogue checks."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if invalidity == "version":
        data["contract_version"] = "999"
    elif invalidity == "identity":
        data["identity"]["name"]["value"] = "A different municipality"
    elif invalidity == "evidence":
        data["capabilities"]["office_hours"]["entries"][0]["hours"][0]["evidence"][0]["excerpt"] = (
            "Invented hours not in the source"
        )
    elif invalidity == "review":
        data["review"]["status"] = "pending"
    else:
        del data["capabilities"]["move_in"]
    source = tmp_path / "discovery.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    artifacts = tmp_path / "artifacts"

    with pytest.raises(BuildError):
        build(source, artifacts)

    assert list(artifacts.glob("build-*")) == []
    assert len(list(artifacts.glob("diagnostic-*/report.md"))) == 1


def test_partial_handoff_package_explains_missing_guidance(tmp_path: Path) -> None:
    """A service handoff permits packaging while prominently preserving missing coverage."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    handoffs = data["capabilities"]["move_in"]["handoffs"]
    data["capabilities"] = {
        key: {"coverage": "unavailable", "missing_reasons": ["not_found"]}
        for key in data["capabilities"]
    }
    data["capabilities"]["move_in"] = {
        "coverage": "handoff_only",
        "handoffs": handoffs,
        "missing_reasons": ["pdf_uninspected"],
    }
    source = tmp_path / "handoff.json"
    source.write_text(json.dumps(data), encoding="utf-8")

    package = build(source, tmp_path / "artifacts")

    report = (package / "report.md").read_text(encoding="utf-8")
    assert "PARTIAL COVERAGE" in report
    assert "0/6" in report
    assert "handoff_only" in report
    assert r"pdf\_uninspected" in report
    assert "https://portal" in report


def test_package_contains_only_runtime_dependencies_and_no_environment_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Factory credentials, tools and model provider code never enter the release."""
    secret = "test-secret-never-publish-718449"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    package = build(FIXTURE, tmp_path)

    assert all(
        secret.encode() not in path.read_bytes() for path in package.rglob("*") if path.is_file()
    )
    runtime = package / "src" / "publicai"
    assert {path.name for path in runtime.glob("*.py")} == {
        "__init__.py",
        "contracts.py",
        "runtime.py",
        "conformance.py",
    }
    dependencies = (package / "pyproject.toml").read_text(encoding="utf-8")
    assert "pydantic-ai" not in dependencies
    assert "openai" not in dependencies
    assert "logfire" not in dependencies


def test_conformance_process_has_no_factory_credentials_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify the process boundary itself, independently of the service implementation."""
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-enter-conformance")
    package = tmp_path / "package"
    modules = package / "src" / "publicai"
    modules.mkdir(parents=True)
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "conformance.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "import socket\n"
        "import subprocess\n"
        "import sys\n"
        "assert 'OPENAI_API_KEY' not in os.environ\n"
        "assert list(Path.home().iterdir()) == []\n"
        "try:\n"
        "    socket.create_connection(('127.0.0.1', 9))\n"
        "except PermissionError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('Network guard did not refuse connection')\n"
        "try:\n"
        "    subprocess.run([sys.executable, '-c', 'pass'], check=True)\n"
        "except PermissionError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('Conformance allowed process spawning')\n",
        encoding="utf-8",
    )

    _run_conformance(package)

    assert list(tmp_path.glob(".conformance-*")) == []


def test_discovery_report_does_not_claim_package_conformance() -> None:
    """Discovery-only CLI output must not claim a build or tests that did not happen."""
    report = render_report(load_discovery(FIXTURE))

    assert "Package conformance has not run" in report
    assert "Shared conformance passed" not in report
    assert "Montag 09:00" in report


def test_failed_conformance_removes_staging_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure after staging still leaves only a diagnostic, never a release."""

    def fail_conformance(package: Path) -> None:
        assert (package / "discovery.json").is_file()
        raise ValueError("Simulated conformance failure")

    monkeypatch.setattr("publicai.builder._run_conformance", fail_conformance)

    with pytest.raises(BuildError) as error:
        build(FIXTURE, tmp_path)

    assert "conformance failure" in error.value.diagnostic_path.read_text(encoding="utf-8")
    assert len(list(tmp_path.iterdir())) == 1
    assert error.value.diagnostic_path.parent.parent == tmp_path
