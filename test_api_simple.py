#!/usr/bin/env python3
"""Simple test for the Vanna AI REST API"""

import requests
import json
import time
import os

def test_api():
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8001")
    base_url = f"http://{host}:{port}"
    
    # Test health endpoint
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/health")
        print(f"Health status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health test failed: {e}")
        return False
    
    # Test learning stats
    print("\nTesting learning stats endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/learning/stats")
        print(f"Learning stats status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Learning stats test failed: {e}")
    
    # Test chat_poll endpoint (replaces old chat endpoint)
    print("\nTesting chat_poll endpoint (v2)...")
    payload = {
        "message": "Show me all tables in the database",
        "headers": {
            "x-user-id": "test_user",
            "x-username": "tester",
            "x-user-groups": "api_users"
        },
        "metadata": {
            "test": True
        }
    }
    
    try:
        response = requests.post(f"{base_url}/api/vanna/v2/chat_poll", json=payload)
        print(f"Chat poll status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Answer: {data.get('answer', '')[:200]}...")
            print(f"SQL: {data.get('sql', 'None')}")
            print(f"CSV URL: {data.get('csv_url', 'None')}")
            print(f"Success: {data.get('success', False)}")
            
            # Test CSV download if available
            csv_url = data.get('csv_url')
            if csv_url:
                csv_response = requests.get(f"{base_url}{csv_url}")
                print(f"CSV download status: {csv_response.status_code}")
                if csv_response.status_code == 200:
                    print(f"CSV size: {len(csv_response.content)} bytes")
                    print(f"CSV first line: {csv_response.text.splitlines()[0][:100]}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Chat poll test failed: {e}")
        return False
    
    # Test health endpoint at root
    print("\nTesting root health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Root health status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Root health test failed: {e}")
    
    return True

if __name__ == "__main__":
    print("Starting API test...")
    # Give server time to start
    time.sleep(2)
    
    if test_api():
        print("\n✅ API test completed successfully!")
    else:
        print("\n❌ API test failed!")
