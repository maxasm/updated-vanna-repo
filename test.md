# Vanna AI REST API – curl Test Commands

This file is a **copy/paste** set of curl commands you can use to test the FastAPI server implemented in `api.py`.

## Prerequisites

Start the REST API (FastAPI/Uvicorn):

```bash
python api.py
```

Notes:

- `python main.py` starts the REST API server (the legacy CLI/TUI has been removed).
- The API requires `OPENAI_API_KEY` and MySQL env vars (`MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`, etc.).

## Setup (recommended)

Define a base URL and a reusable “user identity” payload.

```bash
export BASE_URL="http://localhost:8001"

# IMPORTANT: this API reads "headers" from the JSON body (request_data.headers),
# not from actual HTTP headers.
export VANNA_HEADERS='{"x-user-id":"test_user","x-username":"tester","x-user-groups":"api_users"}'
```

For pretty printing, if you have `jq`:

```bash
alias pj='jq -C .'
```

## 1) Health checks

### Root health (lists endpoints)

```bash
curl -sS "$BASE_URL/health" | jq .
```

### v1 health

```bash
curl -sS "$BASE_URL/api/v1/health" | jq .
```

## 2) Learning endpoints

### Basic stats

```bash
curl -sS "$BASE_URL/api/v1/learning/stats" | jq .
```

### Detailed stats (includes sample patterns)

```bash
curl -sS "$BASE_URL/api/v1/learning/detailed" | jq .
```

### List stored patterns

```bash
curl -sS "$BASE_URL/api/v1/learning/patterns?limit=10" | jq .
curl -sS "$BASE_URL/api/v1/learning/patterns?pattern_type=query&limit=5" | jq .
curl -sS "$BASE_URL/api/v1/learning/patterns?pattern_type=tool&limit=5" | jq .
```

### Test “learning enhancement” of a question

```bash
curl -sS -X POST "$BASE_URL/api/v1/learning/enhance_test" \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "How many customers are there?"
  }' | jq .
```

## 3) Chat (v1) – request/response

`POST /api/v1/chat` returns:

- `answer` (text)
- `sql` (best-effort extraction)
- `csv_url` (if results were saved)
- `success`, `tool_used`, timestamp, user fields

### Minimal “smoke test” chat

```bash
curl -sS -X POST "$BASE_URL/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Hello!",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true}
  }' | jq .
```

### Typical SQL-producing prompts

```bash
curl -sS -X POST "$BASE_URL/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Show me all tables in the database",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true, "case": "tables"}
  }' | jq .

curl -sS -X POST "$BASE_URL/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What are the top 5 most expensive products?",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true, "case": "top-products"}
  }' | jq .

curl -sS -X POST "$BASE_URL/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "List all employees and their offices",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true, "case": "employees"}
  }' | jq .
```

### Error case: missing message (should return 400)

```bash
curl -sS -i -X POST "$BASE_URL/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"headers": '$VANNA_HEADERS'}'
```

## 4) Chat (v2) – polling endpoint

`POST /api/vanna/v2/chat_poll` behaves similarly to v1 chat (request/response).

```bash
curl -sS -X POST "$BASE_URL/api/vanna/v2/chat_poll" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "How many customers are there?",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true, "version": "v2_poll"}
  }' | jq .
```

## 5) Chat (v2) – SSE streaming endpoint

`POST /api/vanna/v2/chat_sse` streams events (Server-Sent Events).

Tip: use `-N` to disable curl buffering.

```bash
curl -N -sS -X POST "$BASE_URL/api/vanna/v2/chat_sse" \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{
    "message": "Show me all tables in the database",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true, "version": "v2_sse"}
  }'
```

You should see lines like:

```text
data: {"event":"start",...}
data: {"event":"chunk","text":"..."}
data: {"event":"sql","sql":"SELECT ..."}
data: {"event":"csv","url":"/static/...csv"}
data: {"event":"complete",...}
```

## 6) Conversation history endpoints

### Get recent conversations

```bash
curl -sS "$BASE_URL/api/v1/conversation/history?user_id=test_user&limit=5" | jq .
```

### Filter conversations by keyword

```bash
curl -sS "$BASE_URL/api/v1/conversation/filter?user_id=test_user&keyword=customers&limit=5" | jq .
```

### Clear conversation history

```bash
curl -sS -X DELETE "$BASE_URL/api/v1/conversation/clear?user_id=test_user" | jq .
```

## 7) Training endpoint (schema training placeholder)

This endpoint iterates over `INFORMATION_SCHEMA.COLUMNS` and returns a count.

```bash
curl -sS -X POST "$BASE_URL/api/v1/train" \
  -H 'Content-Type: application/json' \
  -d '{}' | jq .
```

## 8) CSV download flow (if `csv_url` is returned)

This grabs `csv_url` from the chat response and downloads it.

```bash
CSV_URL=$(curl -sS -X POST "$BASE_URL/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "How many customers are there?",
    "headers": '$VANNA_HEADERS',
    "metadata": {"test": true, "case": "csv-download"}
  }' | jq -r '.csv_url // empty')

echo "csv_url=$CSV_URL"

if [ -n "$CSV_URL" ]; then
  curl -sS "$BASE_URL$CSV_URL" -o results.csv
  echo "Downloaded results.csv"
  head -n 5 results.csv
else
  echo "No csv_url returned (tool may not have run or produced rows)."
fi
```

## Troubleshooting

- **500 with OPENAI_API_KEY error**: ensure `OPENAI_API_KEY` is set in your shell or `.env`.
- **MySQL errors**: ensure `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST` are correct.
- **Long responses**: SQL/tool calls may take 10–60s depending on the model and DB.

## Endpoint map (implemented in `api.py`)

- Health:
  - `GET /health`
  - `GET /api/v1/health`
- Chat:
  - `POST /api/v1/chat`
  - `POST /api/vanna/v2/chat_poll`
  - `POST /api/vanna/v2/chat_sse` (SSE)
  - `WS  /api/vanna/v2/chat_websocket` *(WebSocket; curl is not ideal for this)*
- Learning:
  - `GET /api/v1/learning/stats`
  - `GET /api/v1/learning/detailed`
  - `GET /api/v1/learning/patterns`
  - `POST /api/v1/learning/enhance_test`
- Conversation:
  - `GET /api/v1/conversation/history`
  - `GET /api/v1/conversation/filter`
  - `DELETE /api/v1/conversation/clear`
- Training:
  - `POST /api/v1/train`
- Static files (CSV URLs point here):
  - `GET /static/...`
