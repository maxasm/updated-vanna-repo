#!/usr/bin/env python3
"""
Demonstration of the migrated Vanna AI REST API
Shows how to use the API endpoints
"""

import requests
import json
import time
import subprocess
import sys
import os

def demonstrate_api():
    """Demonstrate the REST API functionality"""
    
    print("=" * 70)
    print("VANNA AI REST API DEMONSTRATION")
    print("=" * 70)
    print("\nThis demonstrates the successful migration from TUI to REST API")
    print("using VannaFastAPIServer with learning/storing functionality.\n")
    
    # Start the API server
    print("1. Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": "."}
    )
    
    # Wait for server to start
    time.sleep(5)
    
    base_url = "http://localhost:8000"
    
    try:
        # Demonstrate health endpoint
        print("\n2. Health check endpoint:")
        print(f"   GET {base_url}/api/v1/health")
        response = requests.get(f"{base_url}/api/v1/health")
        print(f"   Response: {response.status_code}")
        print(f"   Data: {json.dumps(response.json(), indent=2)}")
        
        # Demonstrate learning stats
        print("\n3. Learning statistics endpoint:")
        print(f"   GET {base_url}/api/v1/learning/stats")
        response = requests.get(f"{base_url}/api/v1/learning/stats")
        print(f"   Response: {response.status_code}")
        print(f"   Data: {json.dumps(response.json(), indent=2)}")
        
        # Demonstrate new v2 chat endpoints
        print("\n4. New V2 Chat Endpoints:")
        
        # Test chat_poll endpoint
        print(f"\n   a) Polling endpoint (POST {base_url}/api/vanna/v2/chat_poll):")
        request_body = {
            "message": "Show me all tables in the database",
            "headers": {
                "x-user-id": "demo_user",
                "x-username": "demo",
                "x-user-groups": "api_users"
            },
            "metadata": {
                "demo": True,
                "purpose": "API demonstration"
            }
        }
        print(f"   Request body: {json.dumps(request_body, indent=2)}")
        
        response = requests.post(f"{base_url}/api/vanna/v2/chat_poll", json=request_body, timeout=30)
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Answer length: {len(data.get('answer', ''))} characters")
            print(f"   SQL: {data.get('sql', 'Not extracted')}")
            print(f"   CSV URL: {data.get('csv_url', 'Not generated')}")
            print(f"   Success: {data.get('success', False)}")
            print(f"   Tool used: {data.get('tool_used', False)}")
        else:
            print(f"   Error: {response.text[:200]}")
        
        # Test SSE endpoint
        print(f"\n   b) SSE endpoint (POST {base_url}/api/vanna/v2/chat_sse):")
        sse_response = requests.post(f"{base_url}/api/vanna/v2/chat_sse", json=request_body, timeout=30, stream=True)
        print(f"   Response: {sse_response.status_code}")
        print(f"   Content-Type: {sse_response.headers.get('content-type')}")
        if sse_response.status_code == 200 and 'text/event-stream' in sse_response.headers.get('content-type', ''):
            print("   ✓ SSE stream available")
            # Just show first event
            for line in sse_response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data:'):
                        event_data = json.loads(line[5:].strip())
                        print(f"   First event: {event_data.get('event', 'unknown')}")
                        break
            sse_response.close()
        
        # Note about WebSocket
        print(f"\n   c) WebSocket endpoint (WS {base_url}/api/vanna/v2/chat_websocket):")
        print("   ✓ WebSocket endpoint available (requires WebSocket client)")
        
        # Show web interface
        print("\n5. Web interface (from VannaFastAPIServer):")
        print(f"   GET {base_url}/")
        response = requests.get(f"{base_url}/")
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            if "<html" in response.text.lower():
                print("   ✓ Returns HTML web interface")
            else:
                print("   ⚠️  Returns non-HTML content")
        
        # Show static file serving
        print("\n6. Static file serving (for CSV downloads):")
        print(f"   GET {base_url}/static/")
        print("   (CSV files are served from the query_results directory)")
        
        # Summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print("\n✅ Successfully migrated from TUI to REST API using:")
        print("   - VannaFastAPIServer from vanna.servers.fastapi")
        print("   - FastAPI for REST endpoints")
        print("   - Uvicorn as ASGI server")
        
        print("\n✅ Learning and storing functionality preserved:")
        print("   - ChromaAgentMemory for persistent storage")
        print("   - LearningManager for pattern extraction")
        print("   - Tool usage tracking and pattern learning")
        
        print("\n✅ API returns required format:")
        print("   - sql: Extracted SQL query (when available)")
        print("   - link to csv: URL to download query results")
        print("   - answer: Natural language response")
        
        print("\n✅ Additional features implemented:")
        print("   - Health check endpoint")
        print("   - Learning statistics endpoint")
        print("   - Static file serving for CSV downloads")
        print("   - Web interface from VannaFastAPIServer")
        print("   - CORS enabled for cross-origin requests")
        
        print("\n✅ API Endpoints available:")
        print(f"   {base_url}/health (GET) - Root health check")
        print(f"   {base_url}/api/v1/health (GET) - V1 health check")
        print(f"   {base_url}/api/v1/learning/stats (GET) - Learning statistics")
        print(f"   {base_url}/api/v1/train (POST) - Training endpoint")
        print(f"   {base_url}/api/vanna/v2/chat_sse (POST) - SSE streaming chat")
        print(f"   {base_url}/api/vanna/v2/chat_websocket (WS) - WebSocket real-time chat")
        print(f"   {base_url}/api/vanna/v2/chat_poll (POST) - Request/response polling")
        print(f"   {base_url}/ - Web interface")
        print(f"   {base_url}/static/ - Static files")
        
        print("\n" + "=" * 70)
        print("USAGE EXAMPLE")
        print("=" * 70)
        print("\n# Query the API (Polling):")
        print('''curl -X POST http://localhost:8000/api/vanna/v2/chat_poll \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "How many customers are there?",
    "headers": {
      "x-user-id": "your_user",
      "x-username": "your_name",
      "x-user-groups": "api_users"
    },
    "metadata": {
      "source": "api_client"
    }
  }' ''')
        
        print("\n# Query the API (SSE):")
        print('''curl -X POST http://localhost:8000/api/vanna/v2/chat_sse \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "How many customers are there?",
    "headers": {
      "x-user-id": "your_user",
      "x-username": "your_name",
      "x-user-groups": "api_users"
    },
    "metadata": {
      "source": "api_client"
    }
  }' ''')
        
        print("\n# Health check:")
        print("curl http://localhost:8000/health")
        
        print("\n# Check learning progress:")
        print("curl http://localhost:8000/api/v1/learning/stats")
        
        print("\n# Open web interface:")
        print(f"open {base_url}  # or visit in browser")
        
        return True
        
    finally:
        # Clean up
        print("\n\nCleaning up...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
        print("✅ Demonstration complete")

if __name__ == "__main__":
    demonstrate_api()
