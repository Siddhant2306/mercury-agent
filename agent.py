import os
import asyncio
import time
import argparse
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from dotenv import load_dotenv


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Mercury Agent with configurable MCP server URL')
    parser.add_argument(
        '--mcp-url',
        type=str,
        default='http://localhost:3000/mcp',
        help='MCP server URL (default: http://localhost:3000/mcp)'
    )
    args = parser.parse_args()

    # Try to load environment variables with proper error handling
    env_file = os.environ.get("OPENAI_AGENT_ENV", ".env")

    try:
        # Load environment variables from .env file
        load_dotenv(env_file)

        # Check if OPENAI_API_KEY is set
        if not os.environ.get("OPENAI_API_KEY"):
            print(f"Warning: OPENAI_API_KEY not found in environment or {env_file}")
            print("Please set OPENAI_API_KEY in your .env file or environment")
            return

    except Exception as e:
        print(f"Error loading environment variables from {env_file}: {e}")
        print("Make sure the .env file exists and contains OPENAI_API_KEY=your_key")
        return

    conversation_history = []
    prompt_file = Path(os.environ.get("AGENT_PROMPT_FILE", "prompt.txt"))
    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file '{prompt_file}' not found. Create it or set AGENT_PROMPT_FILE."
        )
    system_prompt = prompt_file.read_text().strip()

    # ---- TIMEOUTS (seconds) ----
    # 1) MCP ClientSession read timeout (THIS is the 5s you're seeing)
    MCP_CLIENT_SESSION_TIMEOUT = 900  # seconds

    # 2) HTTP request timeout to your MCP server
    MCP_HTTP_TIMEOUT = 900  # seconds

    # 3) SSE read timeout (how long to wait for SSE data on stream)
    MCP_SSE_READ_TIMEOUT = 60 * 60  # seconds (1 hour)

    # 4) Outer guard (overall agent run)
    RUN_TIMEOUT_SECONDS = 1800  # seconds

    print(f"Connecting to MCP server at: {args.mcp_url}")

    async with MCPServerStreamableHttp(
        name="unity-mcp",
        params={
            "url": args.mcp_url,
            "timeout": MCP_HTTP_TIMEOUT,            # seconds (NOT ms)
            "sse_read_timeout": MCP_SSE_READ_TIMEOUT,
            # "terminate_on_close": True,           # default True
        },
        cache_tools_list=True,
        client_session_timeout_seconds=MCP_CLIENT_SESSION_TIMEOUT,
    ) as server:
        agent = Agent(
            name="Tester",
            instructions=system_prompt,
            mcp_servers=[server],
        )

        print("Type 'exit' to end the chat.")
        while True:
            user_message = (await asyncio.to_thread(input, "You: ")).strip()
            if not user_message:
                continue
            if user_message.lower() in {"exit", "quit"}:
                print("Agent: Bye!")
                break

            conversation_history.append({"role": "user", "content": user_message})

            try:
                start = time.time()
                out = await asyncio.wait_for(
                    Runner.run(agent, conversation_history, max_turns=100),
                    timeout=RUN_TIMEOUT_SECONDS,
                )
                elapsed = time.time() - start
            except asyncio.TimeoutError:
                print(f"Agent: Timed out after {RUN_TIMEOUT_SECONDS}s (overall run timeout).")
                continue
            except Exception as exc:
                print(f"Agent error: {exc}")
                continue

            conversation_history.append({"role": "assistant", "content": out.final_output})
            print(f"Agent ({elapsed:.2f}s): {out.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
