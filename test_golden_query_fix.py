#!/usr/bin/env python3
"""Test the golden query endpoint fix"""

import json
import requests
import sys

def test_golden_query_endpoint():
    """Test the golden query endpoint with the user's original curl command"""
    
    # Simulate the user's curl command
    url = "http://localhost:8001/api/v1/golden_queries"
    
    headers = {
        "Content-Type": "application/json",
        "x-user-id": "maxwell_test_001"
    }
    
    data = {
        "user_id": "maxwell_test_001",
        "original_question": "Wat is de structuur en betekenis van de belangrijkste velden in de aankoop tabel?",
        "sql_query": "DESCRIBE aankoop",
        "description": "Volledige kolommen van aankooporders: firma = bedrijf/leverancier, leveranciersnaam = naam leverancier, tot_prijs_gel = totaalprijs incl. geld, factuurdatum = datum factuur, leveranciersnr = unieke leverancier ID",
        "tags": ["schema", "aankoop", "documentation"]
    }
    
    print("Testing golden query endpoint...")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print()
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS: Golden query created successfully!")
            result = response.json()
            print(f"Query ID: {result.get('query_id')}")
            return True
        else:
            print(f"\n❌ FAILED: Status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️  WARNING: Could not connect to server. Is the API running?")
        print("To test locally, run: python3 api.py")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def test_with_conversation_id():
    """Test with conversation_id in JSON body"""
    
    url = "http://localhost:8001/api/v1/golden_queries"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "user_id": "test_user_001",
        "conversation_id": "test_conversation_001",
        "original_question": "Test question",
        "sql_query": "SELECT 1",
        "description": "Test description",
        "tags": ["test"]
    }
    
    print("\n\nTesting with conversation_id in JSON body...")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Golden query created with conversation_id in JSON!")
            return True
        else:
            print(f"❌ FAILED: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_with_conversation_id_in_headers():
    """Test with conversation_id in headers"""
    
    url = "http://localhost:8001/api/v1/golden_queries"
    
    headers = {
        "Content-Type": "application/json",
        "x-conversation-id": "header_conversation_001"
    }
    
    data = {
        "user_id": "test_user_002",
        "original_question": "Test question with header conversation_id",
        "sql_query": "SELECT 2",
        "description": "Test with conversation_id in header",
        "tags": ["test", "header"]
    }
    
    print("\n\nTesting with conversation_id in headers...")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Golden query created with conversation_id in headers!")
            return True
        else:
            print(f"❌ FAILED: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Golden Query Endpoint Fix")
    print("=" * 60)
    
    # Start the API server if not running
    import subprocess
    import time
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8001/health", timeout=2)
        print("API server is already running.")
    except:
        print("API server is not running. Starting it now...")
        # Start the server in background
        import threading
        import os
        
        def start_server():
            os.system("python3 api.py > /dev/null 2>&1")
        
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(3)  # Give server time to start
    
    # Run tests
    test1 = test_golden_query_endpoint()
    test2 = test_with_conversation_id()
    test3 = test_with_conversation_id_in_headers()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"Test 1 (Original user request): {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (With conversation_id in JSON): {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Test 3 (With conversation_id in headers): {'✅ PASS' if test3 else '❌ FAIL'}")
    print("=" * 60)
    
    if test1 and test2 and test3:
        print("\n🎉 All tests passed! The fix is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        sys.exit(1)