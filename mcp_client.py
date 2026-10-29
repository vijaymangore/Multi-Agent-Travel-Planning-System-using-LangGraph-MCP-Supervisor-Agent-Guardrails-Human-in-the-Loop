import os
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import (
    AVIATION_STACK_API_KEY,
    OPENWEATHER_API_KEY,
    TAVILY_API_KEY,
)

BASE_DIR = Path(__file__).resolve().parent

# Aviationstack MCP server (uses its own uv-created .venv)
AVIATION_DIR = BASE_DIR / "aviationstack-mcp"
AVIATION_EXE = AVIATION_DIR / ".venv" / "Scripts" / "aviationstack-mcp.exe"

# Weather MCP server: keep weather_mcp_server.py in the project folder,
# or change this path to wherever it really lives
WEATHER_SERVER = BASE_DIR / "weather_mcp_server.py"

# Tavily (remote server, no local files needed)
servers = {
    "tavily": {
        "transport": "streamable_http",
        "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
    },
}

# Local stdio servers are added only if their files exist, so one missing
# file doesn't break every tool with a vague WinError 2
if AVIATION_EXE.exists():
    servers["aviationstack"] = {
        "transport": "stdio",
        "command": str(AVIATION_EXE),
        "args": [],
        "cwd": str(AVIATION_DIR),
        "env": {**os.environ, "AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY},
    }
else:
    print(f"[mcp_client] WARNING: aviationstack server not found: {AVIATION_EXE}")

if WEATHER_SERVER.exists():
    servers["weather"] = {
        "transport": "stdio",
        "command": sys.executable,  # same venv Python that runs Streamlit
        "args": [str(WEATHER_SERVER)],
        "env": {**os.environ, "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY},
    }
else:
    print(f"[mcp_client] WARNING: weather server not found: {WEATHER_SERVER}")

# Create MCP Client
client = MultiServerMCPClient(servers)


# Cache tools so we don't load them repeatedly
_tools_cache = None


async def get_tools():
    global _tools_cache

    if _tools_cache is None:
        try:
            _tools_cache = await client.get_tools()

        except Exception as e:
            print("\n========== FULL ERROR ==========")
            print(type(e))
            print(repr(e))

            if hasattr(e, "exceptions"):
                print("\nSUB EXCEPTIONS:")
                for i, sub in enumerate(e.exceptions):
                    print(f"\n--- Exception {i + 1} ---")
                    print(type(sub))
                    print(repr(sub))

            raise

    return _tools_cache


def _normalize(name: str) -> str:
    # Tavily's tools use hyphens (tavily-search); treat - and _ the same
    return name.replace("-", "_")


async def call_tool(tool_name: str, args: dict = None):
    tools = await get_tools()

    tool = next(
        (t for t in tools if _normalize(t.name) == _normalize(tool_name)),
        None,
    )

    if tool is None:
        available = ", ".join(t.name for t in tools)
        raise ValueError(f"Tool '{tool_name}' not found. Available: {available}")

    return await tool.ainvoke(args or {})


# ------------------------
# Tavily MCP Tools
# ------------------------

async def tavily_search(query: str):
    return await call_tool("tavily_search", {"query": query})


# ------------------------
# Aviationstack MCP Tools
# ------------------------

async def list_airports(search: str = "", limit: int = 10):
    return await call_tool("list_airports", {"search": search, "limit": limit, "offset": 0})


async def list_airlines(search: str = "", limit: int = 10):
    return await call_tool("list_airlines", {"search": search, "limit": limit, "offset": 0})


# ------------------------
# Weather MCP Tools
# ------------------------

async def current_weather(city: str):
    return await call_tool("get_current_weather", {"city": city})


async def forecast(city: str):
    return await call_tool("get_forecast", {"city": city})