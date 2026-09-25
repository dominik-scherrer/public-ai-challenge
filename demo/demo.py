"""End-to-End Demo showcasing live content scraping, inventory generation, and MCP queries."""

import asyncio
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
import httpx
from pydantic_ai.models.test import TestModel

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from public_ai_challenge.phase2_synthesis_gemeinde.agents import (
    data_extraction_agent,
    process_service_content,
    synthesis_agent,
)
from public_ai_challenge.phase2_synthesis_gemeinde.data_generator import generate_inventory
from public_ai_challenge.phase2_synthesis_gemeinde.models import ScoutedService, ServiceProcessingDeps
from public_ai_challenge.phase2_synthesis_gemeinde.server import create_mcp_server


async def run_demo():
    print("=================================================================")
    print("[*] GEMEINDE MCP PIPELINE - LIVE DEMO")
    print("=================================================================\n")

    input_path = Path(__file__).parent / "input" / "scouted_services.json"
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[+] 1. Loading scouted services from '{input_path}'...")
    with open(input_path, "r", encoding="utf-8") as f:
        services_data = json.load(f)

    services = [ScoutedService.model_validate(s) for s in services_data]
    for s in services:
        status_text = "[Available]" if s.available else "[Unavailable]"
        print(f"    - {s.name:<25} | {status_text:<15} | URLs: {len(s.urls)}")

    print("\n[+] 2. Fetching real live web content & generating inventories...")
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    model_name = "openai:gpt-4o" if has_api_key else "test"
    print(f"    OpenAI API Key: {'Detected (using live LLM)' if has_api_key else 'Not set (using demo synthesized models)'}")

    async with httpx.AsyncClient() as client:
        deps = ServiceProcessingDeps(http_client=client, model_name=model_name)

        for service in services:
            print(f"\n    Processing service: '{service.name}'")
            if not has_api_key and service.available:
                synth_data = {
                    "service_name": service.name,
                    "markdown": f"# {service.name}\n\nOffizielle Dienstleistung der Gemeinde Ausserberg.\n\n"
                                f"## Beschreibung\n{service.description}\n\n"
                                f"## Online Schalter\nDie Anmeldung kann online eingereicht werden.",
                    "source_urls": service.urls,
                }
                inv_data = {
                    "service_name": service.name,
                    "json_data": {
                        "schema": "mmp-service-inventory/v0",
                        "id": f"ch.vs.ausserberg.{service.name.lower().replace(' ', '_')}",
                        "title": service.name,
                        "category": "municipal_administration",
                        "summary": service.description,
                        "requirements": ["Gueltiger Ausweis", "Mietvertrag / Kaufvertrag"],
                        "fees": [{"amount": 20, "currency": "CHF", "description": "Meldegebuehr"}],
                        "contacts": [{"department": "Gemeindeverwaltung Ausserberg", "phone": "+41 27 946 21 54"}],
                        "handoffs": [{"url": service.urls[0] if service.urls else "", "type": "online_form"}],
                    },
                }
                with synthesis_agent.override(model=TestModel(custom_output_args=synth_data)), \
                     data_extraction_agent.override(model=TestModel(custom_output_args=inv_data)):
                    synthesized, raw_contents = await process_service_content(service, deps, output_dir=output_dir)
                    await generate_inventory(service, synthesized.markdown, raw_contents, deps, output_dir=output_dir)
            else:
                synthesized, raw_contents = await process_service_content(service, deps, output_dir=output_dir)
                await generate_inventory(service, synthesized.markdown, raw_contents, deps, output_dir=output_dir)

            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in service.name)
            md_file = output_dir / f"{safe_name}.md"
            json_file = output_dir / f"{safe_name}_inventory.json"
            print(f"       -> Markdown generated: {md_file.name} ({md_file.stat().st_size} bytes)")
            print(f"       -> Inventory generated: {json_file.name} ({json_file.stat().st_size} bytes)")

    print("\n[+] 3. Starting FastMCP Server & Loading Municipal Services...")
    server = create_mcp_server(output_dir=output_dir, server_name="Ausserberg-MMP-Server")

    print("\n[+] 4. Simulating MCP Client Invocations:")

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
    print("[OK] DEMO COMPLETED SUCCESSFULLY! All components working smoothly.")
    print("=================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
