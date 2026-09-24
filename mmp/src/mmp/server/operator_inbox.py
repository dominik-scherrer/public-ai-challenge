"""Gap Reports and Feedback — the only two consented channels out (ADR-0005).

Both go to the MMP Operator, not the Municipality. Stored as JSON lines with a
date (no time, no IP, no session, no client identifier), pruned after the
retention period. Gap Reports carry only an abstracted topic; the server
rejects anything that looks like personal data rather than trusting the
client to have abstracted it.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from mmp.registry import OPERATOR_DIR

RETENTION_DAYS = 90  # ADR-0005 assumed default, not yet confirmed by the team
_LOCK = threading.Lock()

_PERSONAL = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "e-mail address"),
    (re.compile(r"(?:\+?\d[\s/-]?){7,}"), "phone or ID number"),
    (re.compile(r"\b\d{4}\s+[A-ZÄÖÜ][a-zäöü]+"), "postal address"),
    (re.compile(r"\b(ich|mein|meine|meinem|meiner|mir|mich)\b", re.I), "first-person wording (not abstracted)"),
    (re.compile(r"https?://"), "link"),
]


class InboxRejected(ValueError):
    pass


def _check_topic(topic: str, limit: int) -> str:
    topic = re.sub(r"\s+", " ", topic or "").strip()
    if not 3 <= len(topic) <= limit:
        raise InboxRejected(f"Topic must be 3–{limit} characters")
    for pattern, what in _PERSONAL:
        if pattern.search(topic):
            raise InboxRejected(f"Topic looks like it contains personal data ({what}); send an abstracted topic only")
    return topic


def _append(name: str, record: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.jsonl"
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    with _LOCK:
        kept = []
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    if date.fromisoformat(json.loads(line)["date"]) >= cutoff:
                        kept.append(line)
                except (ValueError, KeyError):
                    continue
        kept.append(json.dumps(record, ensure_ascii=False))
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def record_gap(bfs: int, topic: str, *, directory: Path = OPERATOR_DIR) -> dict:
    record = {"date": datetime.now(UTC).date().isoformat(), "bfs": int(bfs), "topic": _check_topic(topic, 120)}
    _append("gap-reports", record, directory)
    return record


def record_feedback(bfs: int, service_id: str | None, message: str, *, directory: Path = OPERATOR_DIR) -> dict:
    message = re.sub(r"\s+", " ", message or "").strip()
    if not 3 <= len(message) <= 600:
        raise InboxRejected("Feedback must be 3–600 characters")
    for pattern, what in _PERSONAL[:2]:
        if pattern.search(message):
            raise InboxRejected(f"Please remove personal data ({what}) before sending")
    record = {"date": datetime.now(UTC).date().isoformat(), "bfs": int(bfs), "service_id": service_id, "message": message}
    _append("feedback", record, directory)
    return record
