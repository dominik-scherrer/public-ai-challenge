"""The Reference Client: a small chat page that is an MCP client and an MCP Apps host.

    browser (static/)  --/api/chat-->  this backend  --MCP Streamable HTTP-->  MMP server
         ^                                  |
         |  Service Card (ui:// resource)   |  model: Swiss public AI (PUBLIC_AI_*)
         +--- sandboxed iframe, postMessage-+

Stateless: the browser sends the conversation with every request; nothing is
stored or logged here (no access log, no request bodies in logs).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from mcp.client import Client
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from mmp.client.orchestrator import Orchestrator, RuleModel, clean_situation
from mmp.llm import OpenAICompatibleModel, chat_config
from mmp.registry import handoff_allowlist

STATIC = Path(__file__).parent / "static"
APP_TOOLS = {"send_feedback", "report_gap", "get_service"}  # what a Service Card / host UI may call
log = logging.getLogger("mmp.client")


def _model():
    config = chat_config()
    if config is None:
        return RuleModel(), None
    return OpenAICompatibleModel(config), config


def create_app(mcp_url: str) -> Starlette:
    model, config = _model()
    orchestrator = Orchestrator(mcp_url, model)
    # ADR-0002: the badge may only claim "stays in Switzerland" if that's true. Swisscom's Apertus
    # endpoint is operated in Switzerland, so it defaults to sovereign; anything else must be declared
    # by the operator. MMP_CHAT_SOVEREIGN=false/true always overrides.
    declared = os.getenv("MMP_CHAT_SOVEREIGN", "").strip().lower()
    if declared in {"1", "true", "yes"}:
        sovereign = bool(config)
    elif declared in {"0", "false", "no"}:
        sovereign = False
    else:
        sovereign = bool(config) and config.provider == "swisscom"
    ui_cache: dict[str, str] = {}

    async def config_endpoint(request: Request) -> Response:
        try:
            municipalities = await orchestrator.municipalities()
        except Exception as error:  # noqa: BLE001
            return JSONResponse({"error": f"MMP server not reachable at {mcp_url} ({type(error).__name__})"}, status_code=502)
        return JSONResponse(
            {
                "municipalities": municipalities,
                "default_bfs": int(os.getenv("MMP_DEFAULT_BFS", "4045")),
                "model": model.label,
                "mode": "llm" if config else "rules",
                "sovereign": sovereign,
                "handoff_allowlist": list(handoff_allowlist()),
            }
        )

    async def chat(request: Request) -> Response:
        body = await request.json()
        messages = [
            {"role": m["role"], "content": str(m["content"])[:2000]}
            for m in body.get("messages", [])[-20:]
            if m.get("role") in {"user", "assistant"} and m.get("content")
        ]
        if not messages or messages[-1]["role"] != "user":
            return JSONResponse({"error": "last message must be from the user"}, status_code=400)
        try:
            result = await orchestrator.turn(int(body["bfs"]), messages)
        except Exception as error:  # noqa: BLE001
            log.warning("turn failed: %s", type(error).__name__)  # never the message text
            return JSONResponse({"error": f"Das hat nicht geklappt ({type(error).__name__}). Bitte nochmals versuchen."}, status_code=502)
        return JSONResponse(result)

    async def card(request: Request) -> Response:
        body = await request.json()
        messages = [m for m in body.get("messages", [])[-20:] if m.get("role") in {"user", "assistant"}]
        situation = clean_situation(body.get("situation"))
        try:
            block = await orchestrator.service_card(int(body["bfs"]), str(body["service_id"]), messages, situation)
        except Exception as error:  # noqa: BLE001
            return JSONResponse({"error": type(error).__name__}, status_code=502)
        return JSONResponse(block)

    async def ui_resource(request: Request) -> Response:
        uri = request.query_params.get("uri", "")
        if not uri.startswith("ui://"):
            return JSONResponse({"error": "not a ui:// resource"}, status_code=400)
        if uri not in ui_cache:
            async with Client(mcp_url) as mcp:
                result = await mcp.read_resource(uri)
            content = result.contents[0]
            if "profile=mcp-app" not in (content.mime_type or ""):
                return JSONResponse({"error": "resource is not an MCP App"}, status_code=400)
            ui_cache[uri] = content.text
        return Response(ui_cache[uri], media_type="text/html")

    async def tools_call(request: Request) -> Response:
        """Host-side proxy for tools/call requests coming from a Service Card iframe."""
        body = await request.json()
        name = body.get("name")
        if name not in APP_TOOLS:
            return JSONResponse({"error": f"tool '{name}' is not available to apps"}, status_code=403)
        async with Client(mcp_url) as mcp:
            result = await mcp.call_tool(name, body.get("arguments") or {})
        return JSONResponse(result.model_dump(mode="json", by_alias=True, exclude_none=True))

    async def index(request: Request) -> Response:
        return FileResponse(STATIC / "index.html")

    return Starlette(
        routes=[
            Route("/", index),
            Route("/api/config", config_endpoint),
            Route("/api/chat", chat, methods=["POST"]),
            Route("/api/card", card, methods=["POST"]),
            Route("/api/ui-resource", ui_resource),
            Route("/api/tools/call", tools_call, methods=["POST"]),
            Mount("/static", StaticFiles(directory=STATIC), name="static"),
        ]
    )


def run(host: str = "127.0.0.1", port: int = 8080, mcp_url: str = "http://127.0.0.1:8765/mcp") -> None:
    import uvicorn

    logging.basicConfig(level=logging.WARNING)
    print(f"MMP Reference Client on http://{host}:{port}  (MMP server: {mcp_url})")
    uvicorn.run(create_app(mcp_url), host=host, port=port, access_log=False, log_level="warning")
