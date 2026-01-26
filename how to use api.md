# How to Use the Vanna AI API

This document provides comprehensive documentation on how to use the Vanna AI REST API, including endpoints, request/response formats, authentication, and examples.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication & Headers](#authentication--headers)
- [API Endpoints](#api-endpoints)
  - [Health & Status](#health--status)
  - [Chat Endpoints](#chat-endpoints)
  - [Conversation Management](#conversation-management)
  - [Learning & Statistics](#learning--statistics)
  - [Golden Queries](#golden-queries)
  - [Database & Memory](#database--memory)
  - [Charts & Visualizations](#charts--visualizations)
- [Response Formats](#response-formats)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Vanna AI API is a RESTful service that converts natural language questions into SQL queries, executes them against a connected database, and returns results with optional data visualizations. Key features include:

- **Natural Language to SQL**: Ask questions in plain English, get SQL queries and results
- **Multiple Protocols**: REST, Server-Sent Events (SSE), and WebSocket support
- **Conversation Context**: Maintains context across multiple questions
- **Learning Capabilities**: Improves over time based on successful queries
- **Data Visualization**: Generates charts and graphs from query results
- **Persistent Storage**: Saves conversations, golden queries, and learning patterns

## Quick Start

### 1. Start the API Server
```bash
# From the project directory
python api.py
# or
uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Test the API is Running
```bash
curl http://localhost:8001/health
```

### 3. Send Your First Query
```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user" \
  -H "x-username: test_user" \
  -H "x-user-groups: api_users" \
  -d '{
    "message": "Show me all tables in the database",
    "headers": {
      "x-conversation-id": "my_first_conversation"
    }
  }'
```

## Authentication & Headers

The API uses HTTP headers for user identification and conversation management. While there's no strict authentication, headers are required for proper functionality:

### Required Headers
```http
x-user-id: unique_user_identifier      # Required: Identifies the user
x-username: display_name               # Optional: User's display name
x-user-groups: api_users               # Required: User's group membership
x-conversation-id: conversation_123    # Optional: Conversation identifier
```

### Header Details
- **x-user-id**: Unique identifier for the user (e.g., user ID, email, username)
- **x-username**: Human-readable name for the user (optional)
- **x-user-groups**: Comma-separated list of groups the user belongs to (required for tool access)
- **x-conversation-id**: Identifier for the conversation thread (creates isolated context)

### Example Headers Object
```json
{
  "headers": {
    "x-user-id": "user_123",
    "x-username": "John Doe",
    "x-user-groups": "api_users,premium_users",
    "x-conversation-id": "project_analysis_001"
  }
}
```

## API Endpoints

### Health & Status

#### GET `/health`
Returns overall API health status and lists all available endpoints.

**Response:**
```json
{
  "status": "healthy",
  "service": "vanna-api",
  "timestamp": "2024-01-26T12:34:56.789Z",
  "endpoints": {
    "v1": { ... },
    "v2": { ... },
    "conversation": { ... },
    "learning": { ... }
  }
}
```

#### GET `/api/v1/health`
Simple health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "vanna-api",
  "timestamp": "2024-01-26T12:34:56.789Z",
  "version": "v1"
}
```

### Chat Endpoints

#### POST `/api/v1/chat`
Simple request/response chat endpoint. Best for synchronous applications.

**Request:**
```json
{
  "message": "What are the top 5 products by sales?",
  "headers": {
    "x-user-id": "user_123",
    "x-username": "John",
    "x-user-groups": "api_users",
    "x-conversation-id": "sales_analysis"
  },
  "metadata": {
    "priority": "high",
    "department": "sales"
  }
}
```

**Response:** See [Chat Response Format](#chat-response-format)

#### POST `/api/vanna/v2/chat_sse`
Server-Sent Events streaming endpoint. Returns responses in real-time chunks.

**Request:** Same as `/api/v1/chat`

**Response Stream:**
```
event: start
data: {"event": "start", "timestamp": "2024-01-26T12:34:56.789Z"}

event: chunk
data: {"event": "chunk", "text": "I'll help you"}

event: sql
data: {"event": "sql", "sql": "SELECT * FROM products"}

event: csv
data: {"event": "csv", "url": "/static/query_results/query_abc123.csv"}

event: complete
data: {"event": "complete", "answer": "Full answer here...", "sql": "...", "csv_url": "..."}
```

#### POST `/api/vanna/v2/chat_poll`
Polling endpoint (similar to v1 but with v2 enhancements).

**Request:** Same as `/api/v1/chat`

**Response:** Same format as `/api/v1/chat`

#### WebSocket `/api/vanna/v2/chat_websocket`
Real-time bidirectional communication.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8001/api/vanna/v2/chat_websocket');

ws.onopen = () => {
  ws.send(JSON.stringify({
    "message": "What are the top 5 products?",
    "headers": { ... }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.event, data);
};
```

### Conversation Management

#### GET `/api/v1/conversation/history`
Retrieve conversation history with optional filtering.

**Parameters:**
- `user_identifier` (optional): Filter by user
- `conversation_id` (optional): Filter by conversation
- `limit` (optional, default=10): Number of conversations to return

**Examples:**
```bash
# Get all conversations for a user
curl "http://localhost:8001/api/v1/conversation/history?user_identifier=user_123&limit=5"

# Get specific conversation
curl "http://localhost:8001/api/v1/conversation/history?user_identifier=user_123&conversation_id=sales_analysis&limit=20"
```

#### GET `/api/v1/conversation/filter`
Filter conversations by keyword.

**Parameters:**
- `user_identifier` (optional): Filter by user
- `conversation_id` (optional): Filter by conversation
- `keyword` (optional): Search keyword
- `limit` (optional, default=10): Number of results

**Example:**
```bash
curl "http://localhost:8001/api/v1/conversation/filter?user_identifier=user_123&keyword=sales&limit=5"
```

#### DELETE `/api/v1/conversation/clear`
Clear conversation history.

**Parameters:**
- `user_identifier` (optional): Clear for specific user
- `conversation_id` (optional): Clear specific conversation

**Examples:**
```bash
# Clear specific conversation
curl -X DELETE "http://localhost:8001/api/v1/conversation/clear?user_identifier=user_123&conversation_id=sales_analysis"

# Clear all conversations for a user
curl -X DELETE "http://localhost:8001/api/v1/conversation/clear?user_identifier=user_123"

# Clear all conversations (admin)
curl -X DELETE "http://localhost:8001/api/v1/conversation/clear"
```

### Learning & Statistics

#### GET `/api/v1/learning/stats`
Get basic learning statistics.

**Response:**
```json
{
  "total_queries_processed": 150,
  "successful_queries": 120,
  "failed_queries": 30,
  "success_rate": 0.8,
  "query_patterns_count": 45,
  "tool_patterns_count": 28,
  "last_learning_update": "2024-01-26T12:34:56.789Z"
}
```

#### GET `/api/v1/learning/detailed`
Get detailed learning statistics with examples.

**Response:** Includes example patterns and detailed metrics.

#### GET `/api/v1/learning/patterns`
Get learning patterns with optional filtering.

**Parameters:**
- `pattern_type` (optional): "query" or "tool"
- `limit` (optional, default=10): Number of patterns

**Examples:**
```bash
# Get all patterns
curl "http://localhost:8001/api/v1/learning/patterns?limit=10"

# Get only query patterns
curl "http://localhost:8001/api/v1/learning/patterns?pattern_type=query&limit=5"
```

#### POST `/api/v1/learning/enhance_test`
Test how a question would be enhanced with learned patterns.

**Request:**
```json
{
  "question": "Show me customer orders from last week"
}
```

**Response:**
```json
{
  "original_question": "Show me customer orders from last week",
  "enhanced_question": "Enhanced version with context...",
  "similar_queries_found": 3,
  "similar_queries": [...],
  "similar_tools_found": 2,
  "similar_tools": [...]
}
```

#### POST `/api/v1/train`
Train the agent with database schema information.

**Response:**
```json
{
  "status": "success",
  "trained_items": 150,
  "message": "Trained on 150 schema items"
}
```

### Golden Queries

Golden queries are successful SQL queries that are saved for future reuse.

#### GET `/api/v1/golden_queries`
List golden queries with filtering.

**Parameters:**
- `user_id` (optional): Filter by user
- `conversation_id` (optional): Filter by conversation
- `search` (optional): Text search in question/SQL
- `tags` (optional): Comma-separated list of tags
- `min_success_rate` (optional, default=0.0): Minimum success rate (0.0-1.0)
- `limit` (optional, default=20): Number of results

**Examples:**
```bash
# Get all golden queries for a user
curl "http://localhost:8001/api/v1/golden_queries?user_id=user_123"

# Search for queries about customers
curl "http://localhost:8001/api/v1/golden_queries?search=customer&limit=10"

# Get queries with specific tags
curl "http://localhost:8001/api/v1/golden_queries?tags=sales,monthly&min_success_rate=0.8"
```

#### GET `/api/v1/golden_queries/{query_id}`
Get a specific golden query by ID.

#### POST `/api/v1/golden_queries`
Create or update a golden query.

**Request:**
```json
{
  "user_id": "user_123",
  "conversation_id": "sales_analysis",
  "original_question": "What are the top 5 products by sales?",
  "sql_query": "SELECT product_name, SUM(sales_amount) as total_sales FROM sales GROUP BY product_name ORDER BY total_sales DESC LIMIT 5",
  "description": "Top 5 products by sales volume",
  "tags": ["sales", "products", "top5"],
  "metadata": {
    "department": "sales",
    "frequency": "daily"
  }
}
```

#### POST `/api/v1/golden_queries/{query_id}/record_success`
Record a successful use of a golden query.

#### POST `/api/v1/golden_queries/{query_id}/record_failure`
Record a failed use of a golden query.

#### POST `/api/v1/golden_queries/{query_id}/tags`
Add tags to a golden query.

**Request:**
```json
{
  "tags": ["new_tag", "another_tag"]
}
```

#### DELETE `/api/v1/golden_queries/{query_id}/tags`
Remove tags from a golden query.

#### DELETE `/api/v1/golden_queries/{query_id}`
Delete a golden query.

#### GET `/api/v1/golden_queries/stats`
Get statistics about golden queries.

#### GET `/api/v1/golden_queries/export`
Export golden queries in JSON or CSV format.

**Parameters:**
- `format` (optional, default="json"): "json" or "csv"

**Examples:**
```bash
# Export as JSON
curl "http://localhost:8001/api/v1/golden_queries/export?format=json"

# Export as CSV
curl "http://localhost:8001/api/v1/golden_queries/export?format=csv" -o golden_queries.csv
```

### Database & Memory

#### GET `/api/v1/database/tables`
Get list of tables in the connected database.

**Response:**
```json
{
  "tables": ["customers", "orders", "products", "employees"],
  "count": 4
}
```

#### GET `/api/v1/memory/all`
Get contents of agent memory (ChromaDB).

**Parameters:**
- `limit` (optional, default=100): Number of memory entries

**Example:**
```bash
curl "http://localhost:8001/api/v1/memory/all?limit=20"
```

### Charts & Visualizations

#### GET `/api/v1/charts/{chart_id}/json`
Get chart data as JSON.

#### GET `/api/v1/charts/{chart_id}/html`
Get chart as interactive HTML.

#### GET `/api/v1/charts/{chart_id}/png`
Get chart as PNG image.

#### GET `/api/v1/charts/{chart_id}/download`
Download chart in specified format.

**Parameters:**
- `format` (optional, default="png"): "png", "html", or "json"

**Examples:**
```bash
# Download as PNG
curl "http://localhost:8001/api/v1/charts/chart_abc123/download?format=png" -o chart.png

# Download as HTML
curl "http://localhost:8001/api/v1/charts/chart_abc123/download?format=html" -o chart.html
```

## Response Formats

### Chat Response Format

**Successful Response:**
```json
{
  "answer": "Here are the top 5 products by sales...",
  "sql": "SELECT product_name, SUM(sales_amount) as total_sales FROM sales GROUP BY product_name ORDER BY total_sales DESC LIMIT 5",
  "csv_url": "/static/query_results/query_results_a1b2c3d4.csv",
  "chart": {
    "data": [
      {
        "type": "bar",
        "x": ["Product A", "Product B", "Product C"],
        "y": [15000, 12000, 8500]
      }
    ],
    "layout": {
      "title": "Top Products by Sales",
      "xaxis": {"title": "Product"},
      "yaxis": {"title": "Sales Amount"}
    }
  },
  "chart_info": {
    "chart_id": "chart_abc123",
    "json_url": "/static/charts/chart_abc123.json",
    "html_url": "/static/charts/chart_abc123.html",
    "png_url": "/static/charts/chart_abc123.png",
    "download_url": "/api/v1/charts/chart_abc123/download"
  },
  "success": true,
  "timestamp": "2024-01-26T12:34:56.789Z",
  "tool_used": true,
  "chart_generated": true,
  "chart_source": "vanna_ai_tool",
  "user_id": "user_123",
  "conversation_id": "sales_analysis",
  "username": "John"
}
```

**Key Fields:**
- `answer`: Natural language response
- `sql`: Generated SQL query (if any)
- `csv_url`: URL to download query results as CSV
- `chart`: Plotly chart data (if visualization generated)
- `chart_info`: URLs to access chart in different formats
- `success`: Whether the query was successful
- `tool_used`: Whether any tools (SQL execution, visualization) were used

### Error Response Format

**Standard Error:**
```json
{
  "detail": "Message is required",
  "status": 400,
  "title": "Bad Request",
  "type": "about:blank"
}
```

**Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Error Handling

The API uses standard HTTP status codes:

| Code | Meaning | Typical Causes |
|------|---------|----------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid parameters, missing required fields |
| 404 | Not Found | Endpoint or resource doesn't exist |
| 500