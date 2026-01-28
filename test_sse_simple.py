#!/usr/bin/env python3
"""Simple test for SSE endpoint with new schema"""

import subprocess
import sys
import os
import time
import requests
import json

def test_sse_endpoint():
    """Test the SSE endpoint with curl-like request"""
    print("Testing SSE endpoint with new schema...")
    
    # Test data
    test_data = {
        "message": "Show me all customers",
        "conversation_id": "test-conv-123"
    }
    
    try:
        # Make request with stream=True to get SSE
        response = requests.post(
            "http://localhost:8001/api/vanna/v2/chat_sse",
            json=test_data,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return False
        
        # Read SSE events
        events_received = []
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8').strip()
                print(f"Raw line: {line}")
                
                # Parse SSE format
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        data = json.loads(data_str)
                        events_received.append(data)
                        print(f"Parsed event: {json.dumps(data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"Could not parse JSON: {data_str}")
        
        print(f"\nTotal events received: {len(events_received)}")
        
        # Check if we received expected event types
        event_types = [e.get('event') for e in events_received if isinstance(e, dict)]
        print(f"Event types received: {event_types}")
        
        # Check for required event types from new schema
        required_events = ['start', 'chunk', 'sql', 'complete']
        for req in required_events:
            if req in event_types:
                print(f"✓ Found '{req}' event")
            else:
                print(f"✗ Missing '{req}' event")
        
        # Check event structure
        for event in events_received:
            if isinstance(event, dict):
                event_type = event.get('event')
                print(f"\nChecking {event_type} event structure:")
                
                if event_type == 'start':
                    if 'timestamp' in event:
                        print(f"  ✓ Has timestamp: {event['timestamp']}")
                    else:
                        print(f"  ✗ Missing timestamp")
                
                elif event_type == 'chunk':
                    if 'text' in event:
                        print(f"  ✓ Has text: {event['text'][:50]}...")
                    else:
                        print(f"  ✗ Missing text")
                
                elif event_type == 'sql':
                    if 'sql' in event:
                        print(f"  ✓ Has SQL: {event['sql'][:100]}...")
                    else:
                        print(f"  ✗ Missing SQL")
                
                elif event_type == 'csv':
                    if 'url' in event:
                        print(f"  ✓ Has URL: {event['url']}")
                    else:
                        print(f"  ✗ Missing URL")
                
                elif event_type == 'complete':
                    required_fields = ['answer', 'sql', 'csv_url']
                    for field in required_fields:
                        if field in event:
                            print(f"  ✓ Has {field}")
                        else:
                            print(f"  ✗ Missing {field}")
        
        return len(events_received) > 0
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Start the API server
    print("Starting API server...")
    proc = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5)
    
    try:
        # Test the endpoint
        success = test_sse_endpoint()
        
        if success:
            print("\n✅ SSE endpoint test PASSED!")
        else:
            print("\n❌ SSE endpoint test FAILED!")
            
    finally:
        # Kill the server
        print("Stopping API server...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()