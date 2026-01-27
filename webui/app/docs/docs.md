This document describes the public endpoints of the Vanna AI REST + SSE/WebSocket API.

## Chat & Query Endpoints

These endpoints handle natural language to SQL queries and visualization generation.

| Method | Endpoint                            | Description                                      | Authentication / Headers (optional)                     | Request Body (application/json)                                                                 | Response Content-Type & Format                                                                 |
|--------|-------------------------------------|--------------------------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| POST   | `/api/v1/chat`                      | Synchronous chat – returns complete result       | `x-user-id`, `x-username`, `x-conversation-id`, `x-user-groups` | ```json<br>{<br>  "message": "Top 5 products by revenue in 2025",<br>  "headers": {<br>    "x-conversation-id": "conv_abc123"<br>  },<br>  "conversation_id": "conv_abc123"   // optional if in headers<br>}<br>``` | `application/json`<br>```json<br>{<br>  "answer": "string",<br>  "sql": "string",<br>  "csv_url": "string",<br>  "chart": { ... Plotly dict ... },<br>  "chart_info": { "chart_id": "...", "json_url": "...", ... },<br>  "success": true,<br>  "tool_used": true,<br>  "timestamp": "2026-01-27T..."<br>}<br>``` |
| POST   | `/api/vanna/v2/chat_sse`            | Server-Sent Events – real-time rich streaming    | Same as above                                            | Same structure as `/api/v1/chat`                                                                 | `text/event-stream`<br>Multiple `data: { ... }` lines (rich components)<br>Terminates with `data: [DONE]` |
| POST   | `/api/vanna/v2/chat_poll`           | Polling-style fallback (synchronous)             | Same as above                                            | Same structure as `/api/v1/chat`                                                                 | Same JSON response as `/api/v1/chat`                                                            |
| WS     | `/api/vanna/v2/chat_websocket`      | Bidirectional real-time WebSocket                | Headers sent in first JSON message                       | First message:<br>```json<br>{<br>  "message": "...",<br>  "headers": { ... },<br>  "conversation_id": "..."<br>}<br>``` | JSON frames:<br>`{ "event": "start"\|"chunk"\|"sql"\|"csv"\|"complete"\|"error", ... }`           |

### Detailed SSE Response Format (`/api/vanna/v2/chat_sse`)

- **Content-Type**: `text/event-stream`
- **Structure**: Only `data: {json object}\n\n` lines (no `event:` field)
- **Each line** = one rich UI component update
- **Stream termination**: `data: [DONE]\n\n`

**Rich component schema** (every `data:` payload)

```json
{
  "rich": {
    "id":               "string",           // unique component ID
    "type":             "string",           // e.g. "vanna-status-bar", "text", "dataframe"
    "lifecycle":        "create" | "update",
    "visible":          boolean,
    "interactive":      boolean,
    "timestamp":        "string (ISO 8601)",
    "data":             { ... type-specific payload ... }
  },
  "simple": {                               // optional plain-text fallback
    "type":             "text",
    "text":             "string"
  } | null,
  "conversation_id":    "string",
  "request_id":         "string (UUID)",
  "timestamp":          number              // Unix timestamp with ms
}
```

**Common component types & `data` payloads**

| Type                   | Purpose                                      | Typical `data` keys / example values                                                                 |
|------------------------|----------------------------------------------|------------------------------------------------------------------------------------------------------|
| `vanna-status-bar`     | Global status/loading bar                    | `{ "status": "working"\|"idle"\|"warning", "message": "...", "detail": "..." }`                      |
| `vanna-task-tracker`   | Step-by-step progress                        | `{ "operation": "add_task"\|"update_task", "task": { "title": "...", "status": "completed", ... } }` |
| `notification`         | Toast messages                               | `{ "message": "...", "level": "success"\|"warning"\|"error", "dismissible": true }`                  |
| `dataframe`            | Interactive result table                     | `{ "columns": [...], "data": [[...], ...], "title": "...", "row_count": 42, "description": "..." }`  |
| `text`                 | Main natural-language answer                 | `{ "content": "Markdown supported...", "markdown": true }`                                           |
| `vanna-chat-input`     | Chat input field state                       | `{ "placeholder": "Ask follow-up...", "disabled": false, "focus": true }`                             |

## Conversation Management

| Method | Endpoint                                    | Description                              | Query Params / Body                              | Response Structure                                                                 |
|--------|---------------------------------------------|------------------------------------------|--------------------------------------------------|-------------------------------------------------------------------------------------|
| GET    | `/api/v1/conversation/history`              | Recent conversation turns                | `user_identifier`, `conversation_id`, `limit`    | `{ "conversations": [{ "question", "response", "timestamp", ... }], "count": n }`  |
| GET    | `/api/v1/conversation/filter`               | Keyword-filtered search                  | Same + `keyword`                                 | Same format                                                                         |
| DELETE | `/api/v1/conversation/clear`                | Clear history (scoped or global)         | `user_identifier`, `conversation_id`             | `{ "status": "success", "message": "...", "timestamp": "..." }`                     |

## Chart Endpoints

| Method | Endpoint                                             | Description                              | Parameters / Query                               | Response / Content-Type                          |
|--------|------------------------------------------------------|------------------------------------------|--------------------------------------------------|--------------------------------------------------|
| GET    | `/api/v1/charts/{chart_id}/json`                     | Chart data (Plotly JSON)                 | `chart_id` (path)                                | `application/json` – Plotly figure               |
| GET    | `/api/v1/charts/{chart_id}/html`                     | Interactive Plotly HTML page             | `chart_id` (path)                                | `text/html`                                      |
| GET    | `/api/v1/charts/{chart_id}/png`                      | Static chart image                       | `chart_id` (path)                                | `image/png`                                      |
| GET    | `/api/v1/charts/{chart_id}/download?format=png\|html\|json` | Download chart file                   | `chart_id` (path), `format` (query)              | File attachment with `Content-Disposition`       |

## Golden Queries (Trusted / Saved Queries)

| Method | Endpoint                                             | Description                              | Body / Parameters                                | Response Structure                                   |
|--------|------------------------------------------------------|------------------------------------------|--------------------------------------------------|------------------------------------------------------|
| GET    | `/api/v1/golden_queries`                             | List golden queries                      | `user_id`, `search`, `tags`, `min_success_rate`, `limit` | `{ "golden_queries": [...], "count": n }`            |
| GET    | `/api/v1/golden_queries/{query_id}`                  | Get single golden query                  | `query_id` (path)                                | Single query object                                  |
| POST   | `/api/v1/golden_queries`                             | Create or update golden query            | `{ "user_id", "original_question", "sql_query", "description", "tags": [], ... }` | `{ "status": "success", "query_id": "...", ... }`    |
| POST   | `/api/v1/golden_queries/{query_id}/record_success`   | Log successful usage                     | —                                                | `{ "status": "success" }`                            |
| POST   | `/api/v1/golden_queries/{query_id}/record_failure`   | Log failed usage                         | —                                                | `{ "status": "success" }`                            |

## Learning & System Endpoints

| Method | Endpoint                                             | Description                              | Parameters / Body                                | Response                                             |
|--------|------------------------------------------------------|------------------------------------------|--------------------------------------------------|------------------------------------------------------|
| GET    | `/api/v1/learning/stats`                             | Learning pattern statistics              | —                                                | Statistics object (counts, rates, etc.)              |
| GET    | `/api/v1/learning/patterns`                          | List learned patterns                    | `pattern_type=query\|tool`, `limit`              | `{ "patterns": [...] }`                              |
| POST   | `/api/v1/learning/enhance_test`                      | Test question enhancement                | `{ "question": "..." }`                          | `{ "enhanced_question": "...", "similar_queries": [...] }` |
| GET    | `/health`                                            | API health & endpoint overview           | —                                                | Detailed status + endpoint list                      |
| GET    | `/api/v1/database/tables`                            | List tables in connected database        | —                                                | `{ "tables": ["table1", "table2", ...], "count": n }` |
| GET    | `/api/v1/memory/all?limit=50`                        | Inspect agent memory contents            | `limit` (optional)                               | `{ "memories": [...], "count": n }`                  |

## Static File Serving

- **Mount point**: `/static/*`
- Serves:
  - Generated CSV results: `/static/query_results_xxx.csv`
  - Chart artifacts: `/static/charts/chart_xxx.{json,html,png}`
