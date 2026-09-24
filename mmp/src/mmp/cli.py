"""mmp — command line for the MMP MVP.

    mmp build wettingen                        crawl + extract + Judge + publish
    mmp build wettingen --capture data/captures/wettingen --extraction data/extractions/wettingen.json
    mmp seed                                   rebuild the demo inventories from the committed captures
    mmp serve                                  the shared MMP server (Streamable HTTP, :8765/mcp)
    mmp chat                                   the Reference Client (http://127.0.0.1:8080)
    mmp dev                                    server + client together
    mmp ech0070-import <file.xlsx>             convert the official eCH-0070 list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    here = Path(__file__).resolve()
    for candidate in (Path.cwd() / ".env", here.parents[2] / ".env", here.parents[3] / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


def _print_outcome(outcome) -> None:
    for note in outcome.notes:
        print(f"  - {note}")
    state = "published" if outcome.published else "NOT published"
    print(f"{state}: {outcome.inventory_path}")


def cmd_build(args) -> int:
    from mmp.build.pipeline import build

    outcome = build(
        args.municipality,
        capture_dir=args.capture,
        extraction_path=args.extraction,
        judge_mode=args.judge,
        max_pages=args.max_pages,
    )
    _print_outcome(outcome)
    return 0 if outcome.published else 1


def cmd_seed(args) -> int:
    from mmp.build.pipeline import build
    from mmp.registry import CAPTURE_DIR, EXTRACTION_DIR

    code = 0
    for capture in sorted(p for p in CAPTURE_DIR.iterdir() if p.is_dir()):
        extraction = EXTRACTION_DIR / f"{capture.name}.json"
        if not extraction.exists():
            continue
        print(f"== {capture.name}")
        outcome = build(capture.name, capture_dir=capture, extraction_path=extraction, judge_mode=args.judge)
        _print_outcome(outcome)
        code |= 0 if outcome.published else 1
    return code


def cmd_serve(args) -> int:
    from mmp.server.app import run

    run(host=args.host, port=args.port)
    return 0


def cmd_chat(args) -> int:
    from mmp.client.app import run

    run(host=args.host, port=args.port, mcp_url=args.mcp_url)
    return 0


def cmd_dev(args) -> int:
    import threading
    import time

    from mmp.client.app import run as run_client
    from mmp.server.app import run as run_server

    threading.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": 8765}, daemon=True).start()
    time.sleep(1.0)
    run_client(host=args.host, port=args.port, mcp_url="http://127.0.0.1:8765/mcp")
    return 0


def cmd_ech_import(args) -> int:
    from mmp.build.ech0070 import import_xlsx

    count = import_xlsx(args.xlsx)
    print(f"Imported {count} Leistungen into data/ech0070/leistungen.csv — spot-check a few IDs against the XLSX.")
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_env()
    parser = argparse.ArgumentParser(prog="mmp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Run one Build for a Municipality (slug, name or BFS number)")
    b.add_argument("municipality")
    b.add_argument("--capture", type=Path, help="Use browser-captured pages instead of crawling")
    b.add_argument("--extraction", type=Path, help="Use a saved extraction instead of calling the build model")
    b.add_argument("--judge", choices=["auto", "full", "deterministic"], default="auto")
    b.add_argument("--max-pages", type=int, default=40)
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("seed", help="Rebuild demo inventories from data/captures + data/extractions")
    s.add_argument("--judge", choices=["auto", "full", "deterministic"], default="auto")
    s.set_defaults(func=cmd_seed)

    sv = sub.add_parser("serve", help="Run the shared MMP server (Streamable HTTP)")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8765)
    sv.set_defaults(func=cmd_serve)

    c = sub.add_parser("chat", help="Run the Reference Client")
    c.add_argument("--host", default="127.0.0.1")
    c.add_argument("--port", type=int, default=8080)
    c.add_argument("--mcp-url", default="http://127.0.0.1:8765/mcp")
    c.set_defaults(func=cmd_chat)

    d = sub.add_parser("dev", help="Run MMP server and Reference Client together")
    d.add_argument("--host", default="127.0.0.1")
    d.add_argument("--port", type=int, default=8080)
    d.set_defaults(func=cmd_dev)

    e = sub.add_parser("ech0070-import", help="Import the official eCH-0070 Leistungsinventar XLSX")
    e.add_argument("xlsx", type=Path)
    e.set_defaults(func=cmd_ech_import)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as error:  # noqa: BLE001 - CLI boundary
        from mmp.build.pipeline import BuildError

        if isinstance(error, BuildError):
            print(f"error: {error}", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
