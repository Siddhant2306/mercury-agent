import os
import asyncio
import time
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp


def load_env_value(key: str, env_file: str = ".env") -> str:
    """Load the provided environment variable from a simple KEY=VALUE file."""
    env_path = Path(env_file)
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file '{env_file}' not found")

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        env_key, env_value = line.split("=", 1)
        if env_key.strip() != key:
            continue

        value = env_value.strip().strip('"').strip("'")
        os.environ[key] = value
        return value

    raise KeyError(f"{key} not found in {env_file}")


async def main():
    env_file = os.environ.get("OPENAI_AGENT_ENV", ".env")
    load_env_value("OPENAI_API_KEY", env_file)

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

    async with MCPServerStreamableHttp(
        name="unity-mcp",
        params={
            "url": "http://localhost:3000/mcp",
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
