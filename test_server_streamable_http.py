#!/usr/bin/env python3
# Use uv run test_server.py [host] [port] to run this script
# Make sure to run the server first with `uv run -m ticktick_mcp.cli --transport streamable-http --host [host] --port [port]`
"""
Test script to verify the TickTick MCP server's streamable-http mode.
Starts the server as a subprocess and checks HTTP connectivity.
Usage: python test_streamable_http.py [host] [port]
"""

import sys
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import traceback

async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    session_id = sys.argv[3] if len(sys.argv) > 3 else "testsession"

    try:
        # Connect to a streamable HTTP server
        async with streamablehttp_client(f"http://{host}:{port}/mcp?session={session_id}") as (
            read_stream,
            write_stream,
            _,
        ):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()
                # List available tools
                tools = await session.list_tools()
                print(f"Available tools: {[tool.name for tool in tools.tools]}")
                print("\n✅ Success: MCP streamable-http server is reachable and functional!")
    except Exception as e:
        print("\n❌ ERROR: An exception occurred while testing the streamable-http server:")
        print(f"{type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())