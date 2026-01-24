# Vanna AI REST API - Test Commands

This document provides curl commands to test the migrated Vanna AI REST API.

## Prerequisites

**IMPORTANT:** You need to run the new REST API server, not the old TUI.

1. Start the REST API server:
   ```bash
   python api.py
   ```

   This starts the FastAPI server on port 8000.

2. Or start it in background:
   ```bash
   python api.py &
   ```

3. Wait for server to start (5-10 seconds). You should see output like:
   ```
   INFO:     Started server process [PID]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```

**Note:** `python main.py` starts the old TUI interface. For the REST API, use `python api.py`.

## Base URL
All commands use: `http://localhost:8000`

## Test Commands

### 1. Health Check
```bash
curl -s http://localhost:8000/api/v1/health
```

With pretty JSON output:
```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

### 2. Learning Statistics
```bash
curl -s http://localhost:8000/api/v1/learning/stats
```

With pretty JSON output:
```bash
curl -s http://localhost:8000/api/v1/learning/stats | python3 -m json.tool
```

### 3. Chat Endpoint - Simple Query
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many customers are there?",
    "headers": {
      "x-user-id": "test_user",
      "x-username": "tester",
      "x-user-groups": "api_users"
    },
    "metadata": {
      "test": true
    }
  }'
```

### 4. Chat Endpoint - Table Listing
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all tables in the database",
    "headers": {
      "x-user-id": "test_user",
      "x-username": "tester",
      "x-user-groups": "api_users"
    },
    "metadata": {
      "test": true
    }
  }'
```

### 5. Chat Endpoint - Product Query
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the top 5 most expensive products?",
    "headers": {
      "x-user-id": "test_user",
      "x-username": "tester",
      "x-user-groups": "api_users"
    },
    "metadata": {
      "test": true
    }
  }'
```

### 6. Chat Endpoint - Employee Query
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List all employees and their offices",
    "headers": {
      "x-user-id": "test_user",
      "x-username": "tester",
      "x-user-groups": "api_users"
    },
    "metadata": {
      "test": true
    }
  }'
```

### 7. Training Endpoint
```bash
curl -s -X POST http://localhost:8000/api/v1/train \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 8. Web Interface Check
```bash
curl -s -I http://localhost:8000/
```

## Quick Test Commands (Copy & Paste)

### Health check:
```bash
curl -s http://localhost:8000/api/v1/health
```

### Learning stats:
```bash
curl -s http://localhost:8000/api/v1/learning/stats
```

### Simple chat query:
```bash
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" -d '{"message": "How many customers are there?", "headers": {"x-user-id": "test", "x-username": "tester", "x-user-groups": "api_users"}, "metadata": {"test": true}}'
```

### Table listing:
```bash
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" -d '{"message": "Show me all tables", "headers": {"x-user-id": "test", "x-username": "tester", "x-user-groups": "api_users"}, "metadata": {"test": true}}'
```

### With pretty JSON output:
```bash
curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" -d '{"message": "Show me all tables"}' | python3 -m json.tool
```

## Response Format

The API returns JSON with the following structure:
```json
{
  "answer": "Natural language response from the AI",
  "sql": "Extracted SQL query (when available)",
  "csv_url": "URL to download CSV file (when generated)",
  "success": true/false,
  "timestamp": "ISO timestamp",
  "tool_used": true/false
}
```

## Testing with Response Parsing

### Extract specific fields:
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many customers are there?"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer preview:', data.get('answer', '')[:200]); print('SQL:', data.get('sql', 'None')); print('CSV URL:', data.get('csv_url', 'None')); print('Success:', data.get('success', False))"
```

### Check answer length only:
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many customers are there?"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer length:', len(data.get('answer', '')))"
```

## Testing CSV Download (if CSV URL is provided)

If the response includes a `csv_url` field:
```bash
# First get the CSV URL
CSV_URL=$(curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many customers are there?"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('csv_url', ''))")

# Then download the CSV if URL exists
if [ -n "$CSV_URL" ]; then
  curl -s "http://localhost:8000$CSV_URL" -o results.csv
  echo "CSV downloaded to results.csv"
fi
```

## Troubleshooting

1. **Server not running**: Make sure to start the API server first
2. **Connection refused**: Wait a few seconds for server to start
3. **Timeout**: Some queries may take 10-30 seconds to process
4. **JSON parsing error**: Ensure the curl command has correct JSON syntax

## API Endpoints Summary

- `POST /api/v1/chat` - Main chat endpoint
- `GET /api/v1/learning/stats` - Learning statistics
- `GET /api/v1/health` - Health check
- `POST /api/v1/train` - Training endpoint
- `GET /` - Web interface
- `/static/` - Static files (CSV downloads)
