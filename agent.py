import os
import asyncio
import time
import argparse
from pathlib import Path
import json
from aiohttp import web
from typing import Dict, List, Any

from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from dotenv import load_dotenv


# Global storage for conversation sessions
sessions: Dict[str, List[Dict[str, str]]] = {}

# Global agent instance
agent_instance = None

# Configuration constants
MCP_CLIENT_SESSION_TIMEOUT = 900  # seconds
MCP_HTTP_TIMEOUT = 900  # seconds
MCP_SSE_READ_TIMEOUT = 60 * 60  # seconds (1 hour)
RUN_TIMEOUT_SECONDS = 1800  # seconds


async def chat_handler(request: web.Request) -> web.Response:
    """Handle chat API endpoint"""
    global agent_instance

    if agent_instance is None:
        return web.json_response(
            {"error": "Agent not initialized"},
            status=503
        )

    try:
        # Parse JSON request
        data = await request.json()

        # Validate request
        if "message" not in data:
            return web.json_response(
                {"error": "Missing 'message' field in request body"},
                status=400
            )

        # Get session ID (optional)
        session_id = data.get("session_id", "default")

        # Get or create conversation history for this session
        if session_id not in sessions:
            sessions[session_id] = []

        conversation_history = sessions[session_id]

        # Add user message to history
        user_message = data["message"]
        conversation_history.append({"role": "user", "content": user_message})

        # Run the agent
        start = time.time()
        try:
            out = await asyncio.wait_for(
                Runner.run(agent_instance, conversation_history, max_turns=100),
                timeout=RUN_TIMEOUT_SECONDS,
            )
            elapsed = time.time() - start

            # Add assistant response to history
            conversation_history.append({"role": "assistant", "content": out.final_output})

            # Return success response
            return web.json_response({
                "response": out.final_output,
                "session_id": session_id,
                "elapsed_time": elapsed
            })

        except asyncio.TimeoutError:
            return web.json_response(
                {"error": f"Request timed out after {RUN_TIMEOUT_SECONDS} seconds"},
                status=408
            )
        except Exception as exc:
            return web.json_response(
                {"error": f"Agent error: {str(exc)}"},
                status=500
            )

    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON in request body"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Internal server error: {str(e)}"},
            status=500
        )


async def init_agent(mcp_url: str, system_prompt: str) -> Agent:
    """Initialize the agent with MCP server connection"""
    print(f"Connecting to MCP server at: {mcp_url}")

    mcp_server = MCPServerStreamableHttp(
        name="unity-mcp",
        params={
            "url": mcp_url,
            "timeout": MCP_HTTP_TIMEOUT,
            "sse_read_timeout": MCP_SSE_READ_TIMEOUT,
        },
        cache_tools_list=True,
        client_session_timeout_seconds=MCP_CLIENT_SESSION_TIMEOUT,
    )

    await mcp_server.__aenter__()

    agent = Agent(
        name="Tester",
        instructions=system_prompt,
        mcp_servers=[mcp_server],
    )

    return agent


async def main():
    global agent_instance

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Mercury Agent HTTP API Server')
    parser.add_argument(
        '--mcp-url',
        type=str,
        default='http://localhost:3000/mcp',
        help='MCP server URL (default: http://localhost:3000/mcp)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to run the HTTP server on (default: 8080)'
    )
    args = parser.parse_args()

    # Load prompt file
    prompt_file = Path(os.environ.get("AGENT_PROMPT_FILE", "prompt.txt"))
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file '{prompt_file}' not found. Create it or set AGENT_PROMPT_FILE."
        )
    system_prompt = prompt_file.read_text().strip()

    # Initialize agent
    agent_instance = await init_agent(args.mcp_url, system_prompt)

    # Create web application
    app = web.Application()
    app.router.add_post('/chat', chat_handler)

    # Start server
    print(f"Starting HTTP server on port {args.port}")
    print(f"API endpoint: http://localhost:{args.port}/chat")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', args.port)
    await site.start()

    print("Server is running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
