import requests
import json
import time

BASE_URL = "http://localhost:8001/api/v1"

def test_chat():
    print("Sending chat message...")
    url = f"{BASE_URL}/chat"
    payload = {
        "message": "Show me all tables",
        "user_id": "test_user_1",
        "conversation_id": "test_conv_1"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Chat status: {response.status_code}")
        print(f"Chat response: {response.text[:200]}...")
    except Exception as e:
        print(f"Chat request failed: {e}")
        return

    time.sleep(1)

    print("\nFetching history...")
    url = f"{BASE_URL}/conversation/history"
    try:
        response = requests.get(url)
        print(f"History status: {response.status_code}")
        data = response.json()
        print(f"History count: {data.get('count')}")
        conversations = data.get('conversations', [])
        if conversations:
            print("Found conversations:")
            for conv in conversations:
                print(f"- [{conv['timestamp']}] {conv['question']} -> {conv['response'][:50]}...")
        else:
            print("No conversations found in history.")
    except Exception as e:
        print(f"History request failed: {e}")

if __name__ == "__main__":
    test_chat()
