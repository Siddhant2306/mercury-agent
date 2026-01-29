# Mercury Agent

A conversational AI agent that connects to an MCP (Model Context Protocol) server.

## Usage

### Basic usage (default URL):
```bash
python agent.py
```
This will connect to the default MCP server at `http://localhost:3000/mcp`

### Specify custom MCP server URL:
```bash
python agent.py --mcp-url http://your-server:8080/mcp
```

### Examples:
```bash
# Connect to a local MCP server on a different port
python agent.py --mcp-url http://localhost:5000/mcp

# Connect to a remote MCP server
python agent.py --mcp-url https://api.example.com/mcp

# Get help
python agent.py --help
```

## Environment Variables

- `OPENAI_API_KEY`: Required. Can be set in a `.env` file
- `OPENAI_AGENT_ENV`: Path to the environment file (default: `.env`)
- `AGENT_PROMPT_FILE`: Path to the system prompt file (default: `prompt.txt`)