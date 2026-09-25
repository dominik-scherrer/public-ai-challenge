"""Run the maintained contracts against source-reviewed fictional fixtures."""

from publicai.conformance import check_conformance


def test_shared_conformance() -> None:
    """All published packages must preserve the same six read-only contracts."""
    assert check_conformance() == []
