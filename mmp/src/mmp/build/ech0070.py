"""eCH-0070 mapping (ADR-0001) — only against the official list, never from memory.

The Leistungsinventar (eCH-0070 V4.2.0, Beilage 1) is published as XLSX at
https://www.ech.ch/de/ech/ech-0070/4.2.0. It is not in this repo: the MVP
build host had no network access to ech.ch, and Leistungs-IDs must not be
typed in by hand. Convert the official file once with::

    uv run mmp ech0070-import BEIL1_d&f_eCH-0070_V4.2.0_Leistungsinventar.xlsx

which writes ``data/ech0070/leistungen.csv`` (id;name_de;keywords). Until that
file exists, every Service is ``unmapped`` — which the Service Card shows
honestly as "nicht zugeordnet".

Mapping: candidates are ranked by word overlap between the Service (title,
keywords) and each Leistung (name, keywords); with a model configured, the
model picks one of the top candidates or "none". Without a model only an
exact name match maps. A wrong mapping is worse than none, so ties and weak
matches stay unmapped.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from mmp.llm import ChatModel
from mmp.registry import DATA_DIR
from mmp.schema import Ech0070, Service

CSV_PATH = DATA_DIR / "ech0070" / "leistungen.csv"


@dataclass(frozen=True)
class Leistung:
    id: str
    name: str
    keywords: str


def load_leistungen(path: Path = CSV_PATH) -> list[Leistung]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [
            Leistung(row["id"].zfill(5), row["name_de"], row.get("keywords", ""))
            for row in csv.DictReader(handle, delimiter=";")
            if row.get("id") and row.get("name_de")
        ]


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.casefold()) if len(w) > 3}


def map_service(service: Service, leistungen: list[Leistung], model: ChatModel | None) -> Ech0070:
    if not leistungen:
        return Ech0070()
    target = _words(" ".join([service.title, *service.keywords]))
    scored = sorted(
        ((len(target & _words(f"{l.name} {l.keywords}")), l) for l in leistungen),
        key=lambda pair: -pair[0],
    )
    top = [l for score, l in scored[:8] if score > 0]
    if not top:
        return Ech0070()
    exact = [l for l in top if l.name.casefold() == service.title.casefold()]
    if exact:
        return Ech0070(status="mapped", id=exact[0].id, name=exact[0].name)
    if model is None:
        return Ech0070()
    options = "\n".join(f"{l.id}: {l.name} ({l.keywords})" for l in top)
    answer = model.complete_json(
        "Du ordnest eine Gemeinde-Dienstleistung genau einer eCH-0070-Leistung zu oder keiner. "
        'Antworte mit JSON {"id": "<5-stellige ID oder none>"}. Im Zweifel none.',
        [{"role": "user", "content": f"Dienstleistung: {service.title}\nStichworte: {', '.join(service.keywords)}\n\nKandidaten:\n{options}"}],
    )
    chosen = str(answer.get("id", "none")).strip()
    match = next((l for l in top if l.id == chosen.zfill(5)), None)
    return Ech0070(status="mapped", id=match.id, name=match.name) if match else Ech0070()


def import_xlsx(xlsx_path: Path, out_path: Path = CSV_PATH) -> int:
    """Convert the official XLSX. Column names are detected, not assumed; check the output."""
    from openpyxl import load_workbook  # optional dependency, only for this one-off import

    workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header_row = None
    for row in rows:
        cells = [str(c or "").strip().lower() for c in row]
        if any("id" == c or c.endswith(" id") or "leistungs-id" in c for c in cells):
            header_row = cells
            break
    if header_row is None:
        raise ValueError("Could not find a header row with an ID column; inspect the XLSX and adapt import_xlsx().")

    def col(*needles: str) -> int | None:
        for i, cell in enumerate(header_row):
            if any(n in cell for n in needles):
                return i
        return None

    id_col = col("leistungs-id", "id")
    name_col = col("bezeichnung", "leistung (de)", "name", "leistung")
    kw_col = col("synonym", "deskriptor", "stichw")
    if id_col is None or name_col is None:
        raise ValueError(f"ID/name columns not recognised in header {header_row}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["id", "name_de", "keywords"])
        for row in rows:
            ident, name = row[id_col], row[name_col]
            if not ident or not name or not re.fullmatch(r"\d{1,5}", str(ident).strip()):
                continue
            keywords = row[kw_col] if kw_col is not None else ""
            writer.writerow([str(ident).strip().zfill(5), str(name).strip(), str(keywords or "").strip()])
            count += 1
    return count
