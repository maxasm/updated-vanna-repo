# SSE Chat Endpoint - Production Implementation

This is a production-ready implementation of the `/api/vanna/v2/chat_sse` endpoint that exactly replicates the behavior and event structure of the original implementation.

## Features

✅ **Complete SSE Event Flow**
- `event: start` - Initial timestamp when stream begins
- `event: chunk` - Streaming text chunks (typewriter effect)
- `event: sql` - SQL query when detected
- `event: csv` - CSV file URL when generated
- `event: complete` - Final event with full answer
- `event: error` - Error handling

✅ **Robust CSV Detection**
- Captures CSV filenames from agent text output
- Falls back to latest file detection (30-second window)
- Executes SQL to generate CSV if needed
- Searches recursively in all subdirectories

✅ **SQL Extraction**
- Captures SQL from tool call arguments
- Extracts from code blocks (```sql ... ```)
- Regex patterns for SELECT, SHOW, DESCRIBE
- Keyword-based extraction as fallback

✅ **Production-Ready**
- Comprehensive error handling
- Detailed logging
- Type hints throughout
- Extensive documentation
- Safety limits (max components)
- Timeout protection

## Files

- **`chat_sse_endpoint.py`** - Main implementation
- **`chat_sse_endpoint_example.py`** - Usage examples and client code
- **`README_SSE_ENDPOINT.md`** - This documentation

## Quick Start

### 1. Basic Integration

```python
from fastapi import FastAPI
from chat_sse_endpoint import SSEChatEndpoint, create_sse_endpoint

# Initialize your components
app = FastAPI()
# agent = Agent(...)
# sql_runner = MySQLRunner(...)
# csv_manager = CSVResultManager(...)

# Create SSE handler
sse_handler = SSEChatEndpoint(
    agent=agent,
    sql_runner=sql_runner,
    csv_manager=csv_manager
)

# Register endpoint
create_sse_endpoint(app, sse_handler)
```

### 2. With Optional Components

```python
sse_handler = SSEChatEndpoint(
    agent=agent,
    sql_runner=sql_runner,
    csv_manager=csv_manager,
    conversation_store=conversation_store,        # Optional
    conversation_enhancer=conversation_enhancer,  # Optional
    learning_manager=learning_manager             # Optional
)
```

## API Reference

### Endpoint

**POST** `/api/vanna/v2/chat_sse`

### Request Body

```json
{
  "message": "Show me all tables",
  "headers": {
    "x-user-id": "user123",
    "x-conversation-id": "conv456",
    "x-username": "john_doe"
  },
  "conversation_id": "conv456",  // Fallback if not in headers
  "user_id": "user123"            // Fallback if not in headers
}
```

### Response (SSE Stream)

```
event: start
data: {"event": "start", "timestamp": "2026-01-30T13:06:05.123456"}

event: chunk
data: {"event": "chunk", "text": "Let me check the tables..."}

event: chunk
data: {"event": "chunk", "text": " I'll run a SHOW TABLES query."}

event: sql
data: {"event": "sql", "sql": "SHOW TABLES"}

event: csv
data: {"event": "csv", "url": "/static/query_results/query_results_abc123.csv"}

event: complete
data: {"event": "complete", "answer": "...", "sql": "SHOW TABLES", "csv_url": "/static/..."}
```

## Client Examples

### JavaScript (Browser)

```javascript
const response = await fetch('/api/vanna/v2/chat_sse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Show me all tables',
    headers: { 'x-user-id': 'user123' }
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('event: ')) {
      const eventType = line.substring(7);
    } else if (line.startsWith('data: ')) {
      const data = JSON.parse(line.substring(6));
      
      if (data.event === 'chunk') {
        // Append text to UI
        document.getElementById('response').innerText += data.text;
      } else if (data.event === 'complete') {
        console.log('Complete:', data);
      }
    }
  }
}
```

### Python

```python
import requests
import json

response = requests.post(
    'http://localhost:8000/api/vanna/v2/chat_sse',
    json={
        'message': 'Show me all tables',
        'headers': {'x-user-id': 'user123'}
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            data = json.loads(line[6:])
            
            if data['event'] == 'chunk':
                print(data['text'], end='', flush=True)
            elif data['event'] == 'complete':
                print(f"\n\nFull answer: {data['answer']}")
```

### cURL

```bash
curl -X POST http://localhost:8000/api/vanna/v2/chat_sse \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all tables",
    "headers": {
      "x-user-id": "user123",
      "x-conversation-id": "conv456"
    }
  }'
```

## Architecture

### SSEChatEndpoint Class

The main class that handles all SSE logic:

```python
class SSEChatEndpoint:
    def __init__(self, agent, sql_runner, csv_manager, ...):
        # Initialize with required and optional components
        
    async def handle_sse_request(self, request: Request):
        # Main entry point for SSE requests
        
    async def _event_stream(self, ...):
        # Core streaming logic - yields SSE events
        
    async def _find_csv_file(self, ...):
        # CSV file detection and generation
        
    def _extract_sql_from_response(self, response_text: str):
        # SQL extraction from text
        
    def _format_sse_event(self, event_type: str, data: dict):
        # Format SSE events properly
```

### Event Flow

```
1. Request received
   ↓
2. Parse request body & extract user info
   ↓
3. Enhance question (learned patterns + context)
   ↓
4. Send "start" event
   ↓
5. Stream agent response
   ├─ Send "chunk" events for text
   ├─ Detect SQL from tool calls → Send "sql" event
   └─ Capture CSV filename from text
   ↓
6. After streaming complete:
   ├─ Find CSV file (captured name → latest → generate)
   ├─ Extract SQL if not captured (from text)
   ├─ Send "csv" event if CSV found
   └─ Send "complete" event
   ↓
7. Save conversation history
```

## CSV Detection Strategy

The endpoint uses a multi-layered approach to find CSV files:

1. **Captured Filename** (Highest Priority)
   - Parse agent text for patterns like "Results saved to file: query_results_xxx.csv"
   - Search for exact filename in all subdirectories
   - Check `./query_results/` directory specifically

2. **Latest File Detection** (Fallback)
   - Find most recently modified CSV file
   - Only consider files modified within last 30 seconds
   - Prevents race conditions with other queries

3. **SQL Execution** (Last Resort)
   - If SQL captured but no CSV found
   - Execute SQL query to generate results
   - Save to CSV using CSVResultManager

## SQL Extraction Strategy

Multiple strategies to ensure SQL is captured:

1. **Tool Call Arguments** (Most Reliable)
   - Capture directly from `run_sql` tool call args
   - Send `sql` event immediately when detected

2. **Code Blocks**
   - Extract from ```sql ... ``` blocks
   - Case-insensitive matching

3. **Regex Patterns**
   - SHOW TABLES/DATABASES/COLUMNS
   - SELECT ... FROM ... WHERE ...
   - DESCRIBE table_name
   - SHOW CREATE TABLE

4. **Keyword Search**
   - Find SQL starting with SELECT, SHOW, DESCRIBE, etc.
   - Extract until semicolon or double newline

## Error Handling

- **Request Validation**: Returns 400 if message is missing
- **Agent Timeout**: Sends error event if agent doesn't respond
- **Component Limit**: Safety limit of 100 components to prevent infinite loops
- **Graceful Degradation**: Continues even if optional components fail
- **Detailed Logging**: All errors logged with context

## Headers

The endpoint sets proper SSE headers:

```python
{
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no"  # Disable nginx buffering
}
```

## Testing

### Unit Test Example

```python
import pytest
from chat_sse_endpoint import SSEChatEndpoint

@pytest.mark.asyncio
async def test_sse_endpoint():
    # Mock components
    mock_agent = MockAgent()
    mock_sql_runner = MockSQLRunner()
    mock_csv_manager = MockCSVManager()
    
    # Create handler
    handler = SSEChatEndpoint(
        agent=mock_agent,
        sql_runner=mock_sql_runner,
        csv_manager=mock_csv_manager
    )
    
    # Test request
    request = MockRequest({
        "message": "Show tables",
        "headers": {"x-user-id": "test"}
    })
    
    response = await handler.handle_sse_request(request)
    
    # Verify response
    assert response.media_type == "text/event-stream"
    assert "Cache-Control" in response.headers
```

## Performance Considerations

- **Streaming**: Text chunks sent immediately (no buffering)
- **Async**: Fully async implementation for high concurrency
- **Safety Limits**: Max 100 components to prevent runaway loops
- **Time Windows**: 30-second window for CSV detection
- **Efficient Search**: Recursive glob patterns for file finding

## Differences from Original

This implementation is **functionally identical** to the original but with:

- ✅ Better code organization (separate class)
- ✅ More comprehensive documentation
- ✅ Easier to test and maintain
- ✅ Reusable across projects
- ✅ Type hints throughout
- ✅ Detailed inline comments

## Integration with Existing Code

To integrate into your existing `api.py`:

```python
# In your api.py
from chat_sse_endpoint import SSEChatEndpoint, create_sse_endpoint

# After initializing all your components...
sse_handler = SSEChatEndpoint(
    agent=agent,
    sql_runner=sql_runner,
    csv_manager=csv_manager,
    conversation_store=app.state.conversation_store,
    conversation_enhancer=app.state.conversation_enhancer,
    learning_manager=learning_manager
)

# Register the endpoint
create_sse_endpoint(app, sse_handler)
```

## License

This implementation follows the same license as your main project.

## Support

For issues or questions, please refer to the inline documentation or check the example file.
