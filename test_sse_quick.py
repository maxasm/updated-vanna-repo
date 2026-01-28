import requests
import json
import time

def test_sse():
    """Quick test of SSE endpoint"""
    print("Testing SSE endpoint...")
    
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
            timeout=5
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
        
        # Read first few lines
        line_count = 0
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8').strip()
                print(f"Line {line_count}: {line}")
                line_count += 1
                
                # Stop after 10 lines
                if line_count >= 10:
                    break
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sse()