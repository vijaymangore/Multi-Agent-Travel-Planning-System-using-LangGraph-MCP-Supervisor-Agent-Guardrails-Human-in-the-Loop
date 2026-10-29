import asyncio
from mcp_client import get_tools

async def main():
    tools = await get_tools()
    print([t.name for t in tools])

asyncio.run(main())