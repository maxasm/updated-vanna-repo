"""
Example usage of the SSE chat endpoint.

This file demonstrates how to integrate the SSEChatEndpoint into your FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import the SSE endpoint components
from chat_sse_endpoint import SSEChatEndpoint, create_sse_endpoint

# Import your existing components (adjust imports as needed)
# from your_app import agent, sql_runner, csv_manager, conversation_store, etc.


def setup_sse_endpoint_example():
    """
    Example of how to set up the SSE endpoint in your FastAPI app.
    """
    
    # Create FastAPI app
    app = FastAPI(title="Vanna AI API")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files (for serving CSV files)
    app.mount("/static", StaticFiles(directory="."), name="static")
    
    # Initialize your components (example - adjust to your actual setup)
    # agent = Agent(...)
    # sql_runner = MySQLRunner(...)
    # csv_manager = CSVResultManager(...)
    # conversation_store = ConversationStore(...)
    # conversation_enhancer = ConversationContextEnhancer(...)
    # learning_manager = LearningManager(...)
    
    # Create SSE endpoint handler
    # sse_handler = SSEChatEndpoint(
    #     agent=agent,
    #     sql_runner=sql_runner,
    #     csv_manager=csv_manager,
    #     conversation_store=conversation_store,
    #     conversation_enhancer=conversation_enhancer,
    #     learning_manager=learning_manager
    # )
    
    # Register the endpoint
    # create_sse_endpoint(app, sse_handler)
    
    return app


# Example: Minimal setup without optional components
def setup_minimal_sse_endpoint(agent, sql_runner, csv_manager):
    """
    Minimal example with only required components.
    
    Args:
        agent: Vanna agent instance
        sql_runner: MySQL runner instance
        csv_manager: CSV manager instance
    """
    app = FastAPI()
    
    # Create SSE endpoint handler with minimal components
    sse_handler = SSEChatEndpoint(
        agent=agent,
        sql_runner=sql_runner,
        csv_manager=csv_manager,
        # Optional components can be None
        conversation_store=None,
        conversation_enhancer=None,
        learning_manager=None
    )
    
    # Register the endpoint
    create_sse_endpoint(app, sse_handler)
    
    return app


# Example: Testing the endpoint with curl
"""
# Start event
curl -X POST http://localhost:8000/api/vanna/v2/chat_sse \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all tables in the database",
    "headers": {
      "x-user-id": "user123",
      "x-conversation-id": "conv456",
      "x-username": "john_doe"
    }
  }'

# Expected SSE response:
# event: start
# data: {"event": "start", "timestamp": "2026-01-30T13:06:05.123456"}
#
# event: chunk
# data: {"event": "chunk", "text": "Let me check the tables for you..."}
#
# event: chunk
# data: {"event": "chunk", "text": " I'll run a SHOW TABLES query."}
#
# event: sql
# data: {"event": "sql", "sql": "SHOW TABLES"}
#
# event: chunk
# data: {"event": "chunk", "text": " Results saved to file: query_results_abc123.csv"}
#
# event: csv
# data: {"event": "csv", "url": "/static/query_results/query_results_abc123.csv"}
#
# event: complete
# data: {"event": "complete", "answer": "Let me check the tables for you... I'll run a SHOW TABLES query. Results saved to file: query_results_abc123.csv", "sql": "SHOW TABLES", "csv_url": "/static/query_results/query_results_abc123.csv"}
"""


# Example: JavaScript client for consuming SSE
"""
// JavaScript example for consuming the SSE endpoint
const eventSource = new EventSource('http://localhost:8000/api/vanna/v2/chat_sse', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Show me all tables',
    headers: {
      'x-user-id': 'user123',
      'x-conversation-id': 'conv456'
    }
  })
});

eventSource.addEventListener('start', (e) => {
  const data = JSON.parse(e.data);
  console.log('Stream started:', data.timestamp);
});

eventSource.addEventListener('chunk', (e) => {
  const data = JSON.parse(e.data);
  console.log('Text chunk:', data.text);
  // Append to UI (typewriter effect)
  document.getElementById('response').innerText += data.text;
});

eventSource.addEventListener('sql', (e) => {
  const data = JSON.parse(e.data);
  console.log('SQL query:', data.sql);
  // Display SQL in UI
  document.getElementById('sql-display').innerText = data.sql;
});

eventSource.addEventListener('csv', (e) => {
  const data = JSON.parse(e.data);
  console.log('CSV available:', data.url);
  // Show download link
  document.getElementById('csv-link').href = data.url;
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Stream complete:', data);
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  const data = JSON.parse(e.data);
  console.error('Error:', data.error);
  eventSource.close();
});
"""


# Example: Python client for consuming SSE
"""
import requests
import json

def consume_sse_stream(message, user_id="test_user", conversation_id="test_conv"):
    url = "http://localhost:8000/api/vanna/v2/chat_sse"
    
    payload = {
        "message": message,
        "headers": {
            "x-user-id": user_id,
            "x-conversation-id": conversation_id
        }
    }
    
    response = requests.post(url, json=payload, stream=True)
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            
            # Parse SSE format
            if line.startswith('event: '):
                event_type = line[7:]
            elif line.startswith('data: '):
                data = json.loads(line[6:])
                
                if data['event'] == 'start':
                    print(f"Stream started at {data['timestamp']}")
                
                elif data['event'] == 'chunk':
                    print(data['text'], end='', flush=True)
                
                elif data['event'] == 'sql':
                    print(f"\n\nSQL: {data['sql']}")
                
                elif data['event'] == 'csv':
                    print(f"\nCSV available at: {data['url']}")
                
                elif data['event'] == 'complete':
                    print(f"\n\nComplete! Full answer: {data['answer'][:100]}...")
                    if data['sql']:
                        print(f"SQL: {data['sql']}")
                    if data['csv_url']:
                        print(f"CSV: {data['csv_url']}")
                
                elif data['event'] == 'error':
                    print(f"\nError: {data['error']}")

# Usage
consume_sse_stream("Show me all tables in the database")
"""
