"""Client for querying the minigmeind.suisse.ai MCP server."""

import argparse
import asyncio
import json
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SERVER_URL = "https://minigmeind.suisse.ai/mcp"


async def list_available_tools():
    async with streamable_http_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"Connected to {init.server_info.name} (v{init.server_info.version}, protocol {init.protocol_version})\n")
            tools_res = await session.list_tools()
            print(f"Available tools ({len(tools_res.tools)}):")
            for t in tools_res.tools:
                print(f"  - {t.name:<35} : {t.description}")


async def call_server_tool(tool_name: str, args: dict):
    async with streamable_http_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"Calling tool '{tool_name}' with args {args}...\n")
            result = await session.call_tool(tool_name, args)
            for content in result.content:
                if hasattr(content, "text"):
                    try:
                        parsed = json.loads(content.text)
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except Exception:
                        print(content.text)
                else:
                    print(content)


def main():
    parser = argparse.ArgumentParser(description="Query minigmeind MCP server")
    parser.add_argument("--list", action="store_true", help="List all available tools")
    parser.add_argument("--tool", type=str, help="Tool name to call")
    parser.add_argument("--args", type=str, default="{}", help="JSON arguments for tool call")

    args = parser.parse_args()

    if args.list or not args.tool:
        asyncio.run(list_available_tools())
    else:
        tool_args = json.loads(args.args)
        asyncio.run(call_server_tool(args.tool, tool_args))


if __name__ == "__main__":
    main()
