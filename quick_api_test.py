import subprocess
import time
import requests
import sys
import os
import json
from pathlib import Path

def test_api_with_simple_query():
    """Test the API with a simple query to see if SQL is captured"""
    
    print("Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": "."}
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(10)
    
    try:
        # Test health endpoint
        print("Testing health endpoint...")
        response = requests.get("http://localhost:8001/api/v1/health", timeout=10)
        print(f"Health check status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Health check failed: {response.text}")
            return False
        
        # Test chat endpoint with a simple query
        print("\nTesting chat endpoint...")
        payload = {
            "message": "Show me all tables",
            "headers": {
                "x-user-id": "test_user_123",
                "x-username": "tester",
                "x-user-groups": "api_users"
            }
        }
        
        response = requests.post("http://localhost:8001/api/v1/chat", json=payload, timeout=60)
        print(f"Chat response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse received:")
            print(f"  Answer length: {len(data.get('answer', ''))} chars")
            print(f"  SQL: '{data.get('sql', '')}'")
            print(f"  SQL length: {len(data.get('sql', ''))}")
            print(f"  CSV URL: {data.get('csv_url', 'None')}")
            print(f"  Success: {data.get('success', False)}")
            print(f"  Tool used: {data.get('tool_used', False)}")
            
            # Check if SQL was captured
            sql = data.get('sql', '')
            if sql and sql.strip():
                print(f"\n✓ SUCCESS: SQL was captured!")
                print(f"   SQL preview: {sql[:200]}...")
                return True
            else:
                print(f"\n✗ FAILURE: SQL was not captured (empty or whitespace)")
                
                # Print more details for debugging
                print(f"\nDebug info:")
                print(f"  Response keys: {list(data.keys())}")
                
                # Check answer for SQL patterns
                answer = data.get('answer', '')
                if answer:
                    print(f"\nFirst 1000 chars of answer:")
                    print(answer[:1000])
                    
                    # Check for common SQL patterns in answer
                    import re
                    sql_patterns = [
                        r'```sql\s*(.*?)\s*```',
                        r'SELECT\s+.*?FROM',
                        r'SHOW\s+TABLES',
                        r'information_schema\.tables'
                    ]
                    
                    print(f"\nChecking for SQL patterns in answer:")
                    for pattern in sql_patterns:
                        matches = re.findall(pattern, answer, re.IGNORECASE | re.DOTALL)
                        if matches:
                            print(f"  Found pattern '{pattern}': {len(matches)} matches")
                            for i, match in enumerate(matches[:2]):
                                print(f"    Match {i+1}: {str(match)[:100]}...")
                
                return False
        else:
            print(f"Chat request failed: {response.status_code}")
            print(f"Error: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Kill the API server
        print("\nStopping API server...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
        
        # Print server logs
        stdout, stderr = api_process.communicate()
        if stdout:
            print(f"\nServer stdout (last 1000 chars):")
            print(stdout.decode()[-1000:])
        if stderr:
            print(f"\nServer stderr (last 1000 chars):")
            print(stderr.decode()[-1000:])

if __name__ == "__main__":
    print("=" * 60)
    print("Quick API Test for SQL Capture Fix")
    print("=" * 60)
    
    success = test_api_with_simple_query()
    
    print("\n" + "=" * 60)
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    print("=" * 60)