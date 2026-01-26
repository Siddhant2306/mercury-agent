import os
import asyncio
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

        value = env_value.strip().strip("\"").strip("'")
        os.environ[key] = value
        return value

    raise KeyError(f"{key} not found in {env_file}")

async def main():
    env_file = os.environ.get("OPENAI_AGENT_ENV", ".env")
    load_env_value("OPENAI_API_KEY", env_file)


    conversation_history = []

    async with MCPServerStreamableHttp(
        name="unity-mcp",
        params={"url": "http://localhost:3000/mcp", "timeout": 20},
        cache_tools_list=True,
    ) as server:
        agent = Agent(
            name="Tester",
            instructions="Call the MCP tool test_log with message='hello from agent' and level='info'.",
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

            # Append user message to history
            conversation_history.append({"role": "user", "content": user_message})

            try:
                # Run agent with conversation context
                out = await Runner.run(agent, conversation_history)
            except Exception as exc:  # keep chat alive if MCP/tool call fails
                print(f"Agent error: {exc}")
                continue

            # Append agent response to history
            conversation_history.append({"role": "assistant", "content": out.final_output})
            print(f"Agent: {out.final_output}")

asyncio.run(main())
