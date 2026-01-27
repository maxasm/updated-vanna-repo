Here is the **full, updated API documentation** for your Vanna AI REST API (as implemented in the provided `api.py` file), with the **corrected and accurate SSE description** for `/api/vanna/v2/chat_sse` based on the real Vanna 2.x rich-component streaming behavior.

All endpoints are listed below with method, path, purpose, required/optional input parameters, and expected response structure.

### Chat / Query Endpoints

| Method | Path                              | Purpose                                                                 | Main Input Parameters                                                                 | Main Response Format / Structure                                                                                     |
|--------|-----------------------------------|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| POST   | `/api/v1/chat`                    | Simple synchronous chat (recommended for most use cases)                | JSON body: `message` (req), `headers` (opt), `conversation_id` (opt)                  | JSON: `{ "answer", "sql", "csv_url", "chart", "chart_info", "success", ... }`                                         |
| POST   | `/api/vanna/v2/chat_sse`          | Real-time streaming via Server-Sent Events (rich UI components)         | Same as `/api/v1/chat`                                                                | `text/event-stream` – pure `data: {rich component}` lines (no `event:` field), ends with `data: [DONE]`             |
| WS     | `/api/vanna/v2/chat_websocket`    | Bidirectional real-time WebSocket chat                                  | JSON messages (same structure as above)                                               | JSON events: `start`, `chunk`, `sql`, `csv`, `complete`, `error`                                                      |
| POST   | `/api/vanna/v2/chat_poll`         | Polling-style fallback (behaves like `/api/v1/chat`)                    | Same as `/api/v1/chat`                                                                | Same JSON response as `/api/v1/chat`                                                                                  |

**Detailed SSE behavior (/api/vanna/v2/chat_sse)**

- **Content-Type**: `text/event-stream`
- **Format**: Only `data: {json}\n\n` lines — **no** `event:` field is used
- Each `data:` line contains **one rich UI component**
- Stream ends with: `data: [DONE]\n\n`

**Typical rich component structure** (inside every `data:` line):

```json
{
  "rich": {
    "id": "comp_abc123",
    "type": "vanna-status-bar",           // ← this field tells you what it is
    "lifecycle": "create" | "update",
    "visible": true,
    "interactive": false,
    "timestamp": "2026-01-27T11:45:08.403Z",
    "data": { ... component-specific payload ... }
  },
  "simple": {                             // optional plain-text fallback
    "type": "text",
    "text": "Processing your question..."
  },
  "conversation_id": "conv_xxx",
  "request_id": "req_yyy",
  "timestamp": 1769440988.403561
}
```

**Most common component types you will encounter**

| Component type          | When it appears                              | Typical `data` content examples / purpose                                    |
|-------------------------|----------------------------------------------|--------------------------------------------------------------------------------|
| `vanna-status-bar`      | Almost always first & last                   | `{ "status": "working"|"idle"|"warning", "message": "...", "detail": "..." }` |
| `vanna-task-tracker`    | During thinking / tool execution             | `{ "operation": "add_task"|"update_task", "task": { "title", "status", ... } }` |
| `notification`          | Success, warning, error messages             | `{ "message": "...", "level": "success"|"warning"|"error" }`                   |
| `dataframe`             | When SQL returns tabular results             | `{ "columns": [...], "data": [[...], ...], "title": "...", "row_count": 42 }`  |
| `text`                  | Final natural-language answer (usually last) | `{ "content": "Here is your answer in markdown..." }`                          |
| `vanna-chat-input`      | Input box state changes                      | `{ "placeholder": "...", "disabled": false, "focus": true }`                   |

**Simplified real stream example**

```
data: {"rich":{"type":"vanna-status-bar","data":{"status":"working","message":"Thinking..."}}}
data: {"rich":{"type":"vanna-task-tracker","data":{"operation":"add_task","task":{"title":"Loading context"}}}}
data: {"rich":{"type":"notification","data":{"message":"SQL generated","level":"success"}}}
data: {"rich":{"type":"dataframe","data":{"columns":["name","revenue"],"data":[["Acme",124500],...]}}}
data: {"rich":{"type":"text","data":{"content":"Top customers are..."}}}
data: {"rich":{"type":"vanna-status-bar","data":{"status":"idle"}}}
data: [DONE]
```

### Conversation History Endpoints

| Method   | Path                                      | Purpose                                      | Query Params                                      | Response Structure                                      |
|----------|-------------------------------------------|----------------------------------------------|---------------------------------------------------|-----------------------------------------------------------------|
| GET      | `/api/v1/conversation/history`            | Get recent conversation turns                | `user_identifier`, `conversation_id`, `limit`     | `{ "conversations": [ {question, response, timestamp, ...} ], "count": n }` |
| GET      | `/api/v1/conversation/filter`             | Keyword-filtered conversation search         | same + `keyword`                                  | Same format + filtered results                                  |
| DELETE   | `/api/v1/conversation/clear`              | Clear history (scoped or global)             | `user_identifier`, `conversation_id`              | `{ "status": "success", "message": "...", ... }`                |

### Chart Endpoints

| Method | Path                                         | Purpose                                 | Parameters                        | Response / Content Type              |
|--------|----------------------------------------------|-----------------------------------------|-----------------------------------|--------------------------------------|
| GET    | `/api/v1/charts/{chart_id}/json`             | Chart data as JSON                      | `chart_id` (path)                 | Plotly JSON object                   |
| GET    | `/api/v1/charts/{chart_id}/html`             | Interactive Plotly HTML                 | `chart_id`                        | HTML page                            |
| GET    | `/api/v1/charts/{chart_id}/png`              | Static PNG image                        | `chart_id`                        | `image/png` file                     |
| GET    | `/api/v1/charts/{chart_id}/download?format=...` | Download in format (png, html, json) | `chart_id`, `format` (query)      | File attachment                      |

### Golden Queries Endpoints

| Method | Path                                              | Purpose                                          | Main Parameters / Body                                                                 | Response Structure                                 |
|--------|---------------------------------------------------|--------------------------------------------------|----------------------------------------------------------------------------------------|----------------------------------------------------|
| GET    | `/api/v1/golden_queries`                          | List golden (trusted) queries                    | `user_id`, `search`, `tags`, `min_success_rate`, `limit`                               | `{ "golden_queries": [ ... ], "count": n }`        |
| GET    | `/api/v1/golden_queries/{query_id}`               | Get single golden query                          | `query_id` (path)                                                                      | Single query object                                |
| POST   | `/api/v1/golden_queries`                          | Create / update golden query                     | JSON: `user_id`, `original_question`, `sql_query`, `tags`, `description`, etc.         | `{ "status": "success", "query_id": "...", ... }`  |
| POST   | `/api/v1/golden_queries/{query_id}/record_success` | Record successful usage                          | `query_id`                                                                             | `{ "status": "success" }`                          |
| POST   | `/api/v1/golden_queries/{query_id}/record_failure` | Record failed usage                              | `query_id`                                                                             | `{ "status": "success" }`                          |

### Learning & Admin Endpoints

| Method | Path                                         | Purpose                                          | Parameters / Body                            | Response Structure                                   |
|--------|----------------------------------------------|--------------------------------------------------|----------------------------------------------|------------------------------------------------------|
| GET    | `/api/v1/learning/stats`                     | Learning pattern statistics                      | —                                            | Statistics object (counts, success rates, etc.)      |
| GET    | `/api/v1/learning/patterns`                  | List learned query/tool patterns                 | `pattern_type=query\|tool`, `limit`          | `{ "patterns": [ ... ] }`                            |
| POST   | `/api/v1/learning/enhance_test`              | Test question enhancement with learned patterns  | `{ "question": "..." }`                      | `{ "enhanced_question", "similar_queries", ... }`    |
| GET    | `/api/v1/health`                             | Health check (v1)                                | —                                            | `{ "status": "healthy", "service": "vanna-api", ... }` |
| GET    | `/health`                                    | Root health + endpoint overview                  | —                                            | Detailed health + list of all endpoints              |
| GET    | `/api/v1/database/tables`                    | List tables in connected MySQL database          | —                                            | `{ "tables": ["orders", "customers", ...], "count": n }` |
| GET    | `/api/v1/memory/all?limit=50`                | Peek into Chroma agent memory contents           | `limit` (optional)                           | `{ "memories": [ ... ], "count": n }`                |

### Static File Serving

- **Mount point**: `/static/*`
- Serves:
  - Generated CSV files (`/static/query_results_abc123.csv`)
  - Chart files (`/static/charts/chart_xyz.json`, `.html`, `.png`)