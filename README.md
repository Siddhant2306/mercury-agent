# Mercury Agent API Server

A RESTful HTTP API server for a conversational AI agent that connects to an MCP (Model Context Protocol) server.

## Quick Start

### Basic usage:
```bash
# Start server on default port 8080
python agent.py

# Start server on custom port
python agent.py --port 3000

# Specify custom MCP server URL
python agent.py --mcp-url http://your-server:8080/mcp --port 3000
```

## API Documentation

### Base URL
```
http://localhost:<port>
```

### Endpoints

#### POST `/chat`
Send a message to the AI agent and receive a response.

**Request:**
- Method: `POST`
- Content-Type: `application/json`
- Body:
  ```json
  {
    "message": "Your message here",
    "session_id": "optional-session-id"
  }
  ```

**Request Parameters:**
- `message` (required): The message to send to the agent
- `session_id` (optional): Session identifier to maintain conversation context. If not provided, defaults to "default"

**Response:**
- Content-Type: `application/json`
- Success (200 OK):
  ```json
  {
    "response": "Agent's response here",
    "session_id": "session-id",
    "elapsed_time": 1.23
  }
  ```
- Error responses:
  - 400 Bad Request: Missing required fields or invalid JSON
  - 408 Request Timeout: Agent processing exceeded timeout
  - 500 Internal Server Error: Unexpected error occurred
  - 503 Service Unavailable: Agent not initialized

### Example Usage

#### Using curl:
```bash
# Simple message
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# With session ID
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What did I just ask?", "session_id": "user123"}'
```

#### Using Python:
```python
import requests

# Simple request
response = requests.post(
    "http://localhost:8080/chat",
    json={"message": "Hello, how are you?"}
)
print(response.json())

# With session management
session_id = "user123"
response = requests.post(
    "http://localhost:8080/chat",
    json={
        "message": "Tell me about Python",
        "session_id": session_id
    }
)
print(response.json())
```

#### Using JavaScript:
```javascript
// Simple request
fetch('http://localhost:8080/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Hello, how are you?'
  })
})
.then(response => response.json())
.then(data => console.log(data));

// With session management
const sessionId = 'user123';
fetch('http://localhost:8080/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'What can you help me with?',
    session_id: sessionId
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

## Command Line Arguments

- `--port`: Port to run the HTTP server on (default: 8080)
- `--mcp-url`: MCP server URL (default: http://localhost:3000/mcp)
- `--help`: Show help message

### Examples:
```bash
# Run on port 3000
python agent.py --port 3000

# Connect to a different MCP server
python agent.py --mcp-url https://api.example.com/mcp

# Both custom port and MCP URL
python agent.py --port 5000 --mcp-url http://localhost:4000/mcp
```

## Environment Variables

- `OPENAI_API_KEY`: Required. Can be set in a `.env` file
- `OPENAI_AGENT_ENV`: Path to the environment file (default: `.env`)
- `AGENT_PROMPT_FILE`: Path to the system prompt file (default: `prompt.txt`)

## Session Management

The API supports session management through the `session_id` parameter. Each session maintains its own conversation history:

- If no `session_id` is provided, the "default" session is used
- Each session maintains separate conversation context
- Sessions are stored in memory (will be lost on server restart)

## Error Handling

The API returns appropriate HTTP status codes and error messages:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad request (invalid JSON or missing required fields) |
| 408 | Request timeout (agent processing exceeded timeout) |
| 500 | Internal server error |
| 503 | Service unavailable (agent not initialized) |

Error response format:
```json
{
  "error": "Description of the error"
}
```

## Performance Considerations

- Default timeout for agent processing: 1800 seconds (30 minutes)
- MCP client session timeout: 900 seconds (15 minutes)
- MCP HTTP timeout: 900 seconds (15 minutes)
- MCP SSE read timeout: 3600 seconds (1 hour)

## Requirements

See `requirements.txt` for dependencies. Main requirements:
- aiohttp>=3.9.0
- openai-agents>=0.3.0
- python-dotenv>=1.0.1