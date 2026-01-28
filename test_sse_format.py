import requests
import json
import time

def test_sse_format():
    """Test SSE endpoint format"""
    print("Testing SSE endpoint format...")
    
    test_data = {
        "message": "Show me all customers",
        "conversation_id": "test-conv-123"
    }
    
    try:
        response = requests.post(
            "http://localhost:8001/api/vanna/v2/chat_sse",
            json=test_data,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=10  # Longer timeout
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
        
        # Read events with timeout
        events = []
        start_time = time.time()
        timeout = 10  # 10 seconds total
        
        for line in response.iter_lines():
            if time.time() - start_time > timeout:
                print(f"Timeout after {timeout} seconds")
                break
                
            if line:
                line = line.decode('utf-8').strip()
                print(f"Raw line: {line}")
                
                # Check if this is an event line
                if line.startswith("event: "):
                    event_type = line[7:]  # Remove "event: " prefix
                    print(f"Event type: {event_type}")
                elif line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        data = json.loads(data_str)
                        events.append(data)
                        print(f"Parsed data: {json.dumps(data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"Could not parse JSON: {data_str}")
                
                # Stop if we have enough events
                if len(events) >= 5:
                    print(f"Got {len(events)} events, stopping")
                    break
        
        print(f"\nTotal events received: {len(events)}")
        
        # Check event types
        event_types = []
        for event in events:
            if isinstance(event, dict) and 'event' in event:
                event_types.append(event['event'])
        
        print(f"Event types: {event_types}")
        
        # Check for required events
        required_events = ['start', 'chunk', 'sql', 'complete']
        for req in required_events:
            if req in event_types:
                print(f"✓ Found '{req}' event")
            else:
                print(f"✗ Missing '{req}' event")
        
        return len(events) > 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sse_format()
    if success:
        print("\n✅ SSE format test PASSED!")
    else:
        print("\n❌ SSE format test FAILED!")