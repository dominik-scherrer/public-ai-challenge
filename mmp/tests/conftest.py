import shutil
from pathlib import Path

import pytest

from mmp.registry import CAPTURE_DIR, EXTRACTION_DIR


@pytest.fixture()
def built(tmp_path: Path) -> Path:
    """Seed inventories built into a temp dir through the real pipeline (deterministic Judge)."""
    from mmp.build.pipeline import build

    for slug in ("wettingen", "duebendorf"):
        outcome = build(
            slug,
            capture_dir=CAPTURE_DIR / slug,
            extraction_path=EXTRACTION_DIR / f"{slug}.json",
            judge_mode="deterministic",
            out_dir=tmp_path,
        )
        assert outcome.published, outcome.notes
    return tmp_path


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    for key in ("OPENAI_API_KEY", "PUBLIC_AI_API_KEY", "PUBLIC_AI_ENDPOINT", "PUBLIC_AI_BASE_URL", "PUBLIC_AI_MODEL", "MMP_BUILD_API_KEY"):
        monkeypatch.delenv(key, raising=False)
