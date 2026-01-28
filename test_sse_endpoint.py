import asyncio
import aiohttp
import json
import time
import subprocess
import sys
import os
from contextlib import asynccontextmanager

async def test_sse_endpoint():
    """Test the SSE endpoint with the new schema"""
    print("Testing SSE endpoint with new schema...")
    
    # Test data
    test_data = {
        "question": "Show me all customers",
        "conversation_id": "test-conv-123"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8001/ask",
                json=test_data,
                headers={"Accept": "text/event-stream"}
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.status != 200:
                    print(f"Error: {await response.text()}")
                    return False
                
                # Read SSE events
                events_received = []
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        print(f"Received: {line}")
                        
                        # Parse SSE format
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            try:
                                data = json.loads(data_str)
                                events_received.append(data)
                                print(f"Parsed event: {data}")
                            except json.JSONDecodeError:
                                print(f"Could not parse JSON: {data_str}")
                
                print(f"\nTotal events received: {len(events_received)}")
                
                # Check if we received expected event types
                event_types = [e.get('event') for e in events_received if isinstance(e, dict)]
                print(f"Event types received: {event_types}")
                
                # Check for required event types
                required_events = ['start', 'chunk', 'sql', 'complete']
                for req in required_events:
                    if req in event_types:
                        print(f"✓ Found '{req}' event")
                    else:
                        print(f"✗ Missing '{req}' event")
                
                return len(events_received) > 0
                
    except Exception as e:
        print(f"Error during test: {e}")
        return False

async def main():
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
        success = await test_sse_endpoint()
        
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
    asyncio.run(main())