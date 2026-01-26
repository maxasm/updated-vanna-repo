# Vanna AI API

A REST API server for Vanna AI application using FastAPI. This API provides natural language to SQL query capabilities with learning/storing capabilities, conversation management, and data visualization features.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the API](#running-the-api)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [Chat Endpoints](#chat-endpoints)
  - [Conversation Management](#conversation-management)
  - [Learning & Statistics](#learning--statistics)
  - [Database & Memory](#database--memory)
- [Test Curl Requests](#test-curl-requests)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Environment Variables](#environment-variables)

## Overview

The Vanna AI API transforms natural language questions into SQL queries, executes them against a connected database, and returns results with optional data visualizations. Key features include:

- **Natural Language to SQL**: Convert plain English questions into SQL queries
- **Conversation Context**: Maintain conversation history with user isolation
- **Learning Capabilities**: Improve responses over time based on successful queries
- **Data Visualization**: Generate charts and visualizations from query results
- **Multiple Protocols**: Support for REST, Server-Sent Events (SSE), and WebSockets

## Prerequisites

- Python 3.8+
- MySQL database (or compatible SQL database)
- OpenAI API key
- Required Python packages (see `requirements.txt`)

## Installation & Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd vanna-ai-app
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running the API

Start the API server:
```bash
python api.py
```

Or using uvicorn directly:
```bash
uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Root health check with endpoint listing |
| GET | `/api/v1/health` | Simple health check |

### Chat Endpoints

| Method | Endpoint | Description | Protocol |
|--------|----------|-------------|----------|
| POST | `/api/v1/chat` | Simple chat with request/response | REST |
| POST | `/api/vanna/v2/chat_sse` | Streaming chat with Server-Sent Events | SSE |
| POST | `/api/vanna/v2/chat_poll` | Chat with polling (similar to v1) | REST |
| WS | `/api/vanna/v2/chat_websocket` | Real-time chat via WebSocket | WebSocket |

### Conversation Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/conversation/history` | Get conversation history |
| GET | `/api/v1/conversation/filter` | Filter conversations by keyword |
| DELETE | `/api/v1/conversation/clear` | Clear conversation history |

### Learning & Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/learning/stats` | Get learning statistics |
| GET | `/api/v1/learning/detailed` | Get detailed learning stats with examples |
| GET | `/api/v1/learning/patterns` | Get learning patterns |
| POST | `/api/v1/learning/enhance_test` | Test learning enhancement on a question |
| POST | `/api/v1/train` | Train the agent with schema information |

### Database & Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/database/tables` | Get list of tables in database |
| GET | `/api/v1/memory/all` | Get contents of agent memory |

## Test Curl Requests

### Base Configuration
```bash
# Base URL
BASE_URL="http://localhost:8001"

# Common headers for authentication
COMMON_HEADERS=(
  -H "Content-Type: application/json"
  -H "x-user-id: test_user"
  -H "x-username: test_user"
  -H "x-user-groups: api_users"
)
```

### 1. Health Check
```bash
# Root health check with endpoint listing
curl -X GET "${BASE_URL}/health"

# Simple health check (v1)
curl -X GET "${BASE_URL}/api/v1/health"
```

### 2. Chat Endpoints

#### Simple Chat (v1)
```bash
curl -X POST "${BASE_URL}/api/v1/chat" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "message": "Show me the list of tables in the database",
    "headers": {
      "x-conversation-id": "test_conversation_001"
    }
  }'
```

#### Streaming Chat with SSE (v2)
```bash
curl -N -X POST "${BASE_URL}/api/vanna/v2/chat_sse" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "message": "Get me a summary of sales data",
    "headers": {
      "x-conversation-id": "test_conversation_002"
    }
  }'
```

#### Polling Chat (v2)
```bash
curl -X POST "${BASE_URL}/api/vanna/v2/chat_poll" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "message": "What are the top 5 products by sales?",
    "headers": {
      "x-conversation-id": "test_conversation_003"
    }
  }'
```

### 3. Conversation Management

#### Get Conversation History
```bash
# Get all conversations for a user
curl -X GET "${BASE_URL}/api/v1/conversation/history?user_identifier=test_user&limit=5" \
  "${COMMON_HEADERS[@]}"

# Get specific conversation thread
curl -X GET "${BASE_URL}/api/v1/conversation/history?user_identifier=test_user&conversation_id=test_conversation_001&limit=10" \
  "${COMMON_HEADERS[@]}"
```

#### Filter Conversations by Keyword
```bash
curl -X GET "${BASE_URL}/api/v1/conversation/filter?user_identifier=test_user&keyword=sales&limit=5" \
  "${COMMON_HEADERS[@]}"
```

#### Clear Conversation History
```bash
# Clear specific conversation
curl -X DELETE "${BASE_URL}/api/v1/conversation/clear?user_identifier=test_user&conversation_id=test_conversation_001" \
  "${COMMON_HEADERS[@]}"

# Clear all conversations for a user
curl -X DELETE "${BASE_URL}/api/v1/conversation/clear?user_identifier=test_user" \
  "${COMMON_HEADERS[@]}"

# Clear all conversations (admin only)
curl -X DELETE "${BASE_URL}/api/v1/conversation/clear" \
  "${COMMON_HEADERS[@]}"
```

### 4. Learning & Statistics

#### Get Learning Statistics
```bash
curl -X GET "${BASE_URL}/api/v1/learning/stats" \
  "${COMMON_HEADERS[@]}"
```

#### Get Detailed Learning Stats
```bash
curl -X GET "${BASE_URL}/api/v1/learning/detailed" \
  "${COMMON_HEADERS[@]}"
```

#### Get Learning Patterns
```bash
# Get all patterns
curl -X GET "${BASE_URL}/api/v1/learning/patterns?limit=10" \
  "${COMMON_HEADERS[@]}"

# Get query patterns only
curl -X GET "${BASE_URL}/api/v1/learning/patterns?pattern_type=query&limit=5" \
  "${COMMON_HEADERS[@]}"

# Get tool patterns only
curl -X GET "${BASE_URL}/api/v1/learning/patterns?pattern_type=tool&limit=5" \
  "${COMMON_HEADERS[@]}"
```

#### Test Learning Enhancement
```bash
curl -X POST "${BASE_URL}/api/v1/learning/enhance_test" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "question": "Show me customer orders from last week"
  }'
```

#### Train the Agent
```bash
curl -X POST "${BASE_URL}/api/v1/train" \
  "${COMMON_HEADERS[@]}"
```

### 5. Database & Memory

#### Get Database Tables
```bash
curl -X GET "${BASE_URL}/api/v1/database/tables" \
  "${COMMON_HEADERS[@]}"
```

#### Get Agent Memory Contents
```bash
# Get first 10 memory entries
curl -X GET "${BASE_URL}/api/v1/memory/all?limit=10" \
  "${COMMON_HEADERS[@]}"

# Get first 50 memory entries
curl -X GET "${BASE_URL}/api/v1/memory/all?limit=50" \
  "${COMMON_HEADERS[@]}"
```

## Response Format

### Successful Chat Response
```json
{
  "answer": "Here are the tables in your database: customers, orders, products, employees...",
  "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'your_database'",
  "csv_url": "/static/query_results/query_results_a1b2c3d4.csv",
  "chart": {
    "data": [
      {
        "type": "bar",
        "x": ["customers", "orders", "products"],
        "y": [150, 1200, 85]
      }
    ],
    "layout": {
      "title": "Table Counts",
      "xaxis": {"title": "Table Name"},
      "yaxis": {"title": "Count"}
    }
  },
  "chart_image_url": "/static/charts/test_conversation_001/query_results_a1b2c3d4_visualization.png",
  "success": true,
  "timestamp": "2024-01-26T12:34:56.789Z",
  "tools_used": ["run_sql", "visualize_data"],
  "user_id": "test_user",
  "conversation_id": "test_conversation_001",
  "username": "test_user"
}
```

### Error Response
```json
{
  "detail": "Message is required",
  "status": 400,
  "title": "Bad Request",
  "type": "about:blank"
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200 OK`: Request succeeded
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Endpoint or resource not found
- `500 Internal Server Error`: Server-side error

## Environment Variables

Create a `.env` file with the following variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
MYSQL_DO_HOST=localhost
MYSQL_DO_DATABASE=your_database
MYSQL_DO_USER=your_username
MYSQL_DO_PASSWORD=your_password
MYSQL_DO_PORT=3306

# Server Configuration
HOST=0.0.0.0
PORT=8001
LOG_LEVEL=info

# JWT Configuration (optional)
JWT_SECRET_KEY=your_secret_key_here
```

## Testing Scripts

The repository includes two testing scripts:

1. **`curl_commands.sh`** - Formatted curl commands with explanations
2. **`curl_commands_inline.sh`** - Inline curl commands for easy copy-paste

Run the test scripts:
```bash
# Make scripts executable
chmod +x curl_commands.sh curl_commands_inline.sh

# Run formatted commands
./curl_commands.sh

# Run inline commands
./curl_commands_inline.sh
```

## Notes

- The API uses Vanna AI 2.x for natural language to SQL conversion
- Conversation history is isolated per (user_id, conversation_id) pair
- CSV files and chart images are served via the `/static/` endpoint
- Learning patterns improve response quality over time
- WebSocket and SSE endpoints provide real-time streaming capabilities

For more detailed information about the API implementation, see `API_IMPROVEMENTS_SUMMARY.md`.