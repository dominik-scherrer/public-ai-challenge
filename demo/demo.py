"""End-to-End Demo showcasing live content scraping, inventory generation, Judge evaluation, and MCP queries using pipeline interfaces."""

import asyncio
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from public_ai_challenge.core import (
    JudgeProtocol,
    McpServerProtocol,
    ScoutProtocol,
    SynthesisProtocol,
)
from public_ai_challenge.phase1_scout.adapter import FinalScoutAdapter
from public_ai_challenge.phase2_synthesis.adapter import FinalSynthesisAdapter
from public_ai_challenge.phase4_mcp.adapter import McpServerGemeindeAdapter
from public_ai_challenge.phase3_judge.adapter import JudgePipelineAdapter


async def run_demo():
    print("=================================================================")
    print("[*] MODEL MUNICIPALITY PROTOCOL (MMP) - PIPELINE DEMO")
    print("=================================================================\n")

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    model_name = "openai:gpt-4o" if has_api_key else "test"
    print(f"[*] Configuration:")
    print(f"    OpenAI API Key: {'Detected (using live LLM)' if has_api_key else 'Not set (using demo synthesized models)'}")
    print(f"    Output Directory: {output_dir}")

    # -------------------------------------------------------------
    # 1. Initialize Pipeline Stage Implementations (Protocols)
    # -------------------------------------------------------------
    scout: ScoutProtocol = FinalScoutAdapter(use_agent=False)  # Using heuristic agent to speed up demo
    synthesis: SynthesisProtocol = FinalSynthesisAdapter(model_name=model_name)
    judge: JudgeProtocol = JudgePipelineAdapter(build_floor=0.0)
    mcp_server: McpServerProtocol = McpServerGemeindeAdapter()

    # -------------------------------------------------------------
    # Phase 1: Scout Stage
    # -------------------------------------------------------------
    print("\n[+] [Phase 1: Scout] Scouting municipal services...")
    scout_result = await scout.scout(
        url="https://www.ausserberg.ch",
        municipality="Ausserberg",
        canton="VS",
        output_dir=output_dir,
    )
    print(f"    Municipality: {scout_result.municipality_name} ({scout_result.canton})")
    print(f"    Discovered services: {len(scout_result.services)}")
    for s in scout_result.services:
        status_text = "[Available]" if s.available else "[Unavailable]"
        print(f"      - {s.name:<25} | {status_text:<15} | URLs: {len(s.urls)}")

    # -------------------------------------------------------------
    # Phase 2: Synthesis Stage
    # -------------------------------------------------------------
    print("\n[+] [Phase 2: Synthesis] Synthesizing markdown & extracting service inventories...")
    inventory_records = await synthesis.synthesize(scout_result, output_dir=output_dir)
    for rec in inventory_records:
        md_name = Path(rec.markdown_path).name if rec.markdown_path else "N/A"
        inv_name = Path(rec.inventory_path).name if rec.inventory_path else "N/A"
        print(f"      - {rec.service_name:<25} -> {md_name} & {inv_name}")

    # -------------------------------------------------------------
    # Phase 3: Judge Stage (Quality Gate)
    # -------------------------------------------------------------
    print("\n[+] [Phase 3: Judge] Running automated quality gate evaluation...")
    judge_report = await judge.evaluate(
        inventory_records=inventory_records,
        scout_result=scout_result,
        dry_run=True,
    )
    print(f"    Build ID: {judge_report.build_id}")
    print(f"    Gate Status: {'[PASSED]' if judge_report.passed else '[BLOCKED]'}")
    print(f"    Coverage Ratio: {judge_report.coverage_ratio * 100:.1f}%")
    print(f"    Evaluated findings: {len(judge_report.findings)}")
    print(f"    Withheld fields (unsupported claims): {len(judge_report.withheld_fields)}")

    # -------------------------------------------------------------
    # Phase 4: MCP Serving Stage
    # -------------------------------------------------------------
    print("\n[+] [Phase 4: MCP Serving] Starting FastMCP Server & Loading Municipal Services...")
    server = mcp_server.create_server(
        inventory_records=inventory_records,
        output_dir=output_dir,
        server_name="Ausserberg-MMP-Server",
    )

    print("\n[+] Simulating MCP Client Invocations:")

    # Tool call: list_services
    list_res = await server.call_tool("list_services", {})
    all_services = list_res.structured_content["result"]
    print(f"\n    [Tool] list_services()")
    print(f"           Result: {all_services}")

    # Tool call: get_service
    target_svc = "Anmeldung_Wohnsitz"
    get_res = await server.call_tool("get_service", {"service_name": target_svc})
    print(f"\n    [Tool] get_service('{target_svc}')")
    print(f"           Result Preview:\n{json.dumps(get_res.structured_content['result'], indent=6)[:320]}...\n      }}")

    # Tool call: search_services
    search_query = "Gemeindeanlagen"
    search_res = await server.call_tool("search_services", {"query": search_query})
    print(f"\n    [Tool] search_services('{search_query}')")
    print(f"           Result: {search_res.structured_content['result']}")

    # Reading MCP Resource
    resource_uri = f"gemeinde://services/{target_svc}"
    res = await server.read_resource(resource_uri)
    print(f"\n    [Resource] read_resource('{resource_uri}')")
    print("               Markdown Content:")
    for line in res[0].content.splitlines()[:6]:
        print(f"               | {line}")

    print("\n=================================================================")
    print("[OK] FULL PIPELINE COMPLETED SUCCESSFULLY VIA ABSTRACT INTERFACES!")
    print("=================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
