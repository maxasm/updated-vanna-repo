#!/usr/bin/env python3
"""Test the new Vanna API v2 endpoints"""

import requests
import json
import time
import subprocess
import sys
import os
import asyncio
import websockets
import threading

def start_server():
    """Start the API server in a separate process"""
    print("Starting API server...")
    process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": "."}
    )
    time.sleep(5)  # Wait for server to start
    return process

def test_health_endpoints():
    """Test health check endpoints"""
    print("\n1. Testing health endpoints:")
    
    # Test root health endpoint
    print(f"   GET http://localhost:8000/health")
    response = requests.get("http://localhost:8000/health")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)}")
    
    # Test v1 health endpoint
    print(f"\n   GET http://localhost:8000/api/v1/health")
    response = requests.get("http://localhost:8000/api/v1/health")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)}")
    
    return response.status_code == 200

def test_chat_poll():
    """Test the polling chat endpoint"""
    print("\n2. Testing chat_poll endpoint (POST /api/vanna/v2/chat_poll):")
    
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
    
    print(f"   POST http://localhost:8000/api/vanna/v2/chat_poll")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post("http://localhost:8000/api/vanna/v2/chat_poll", 
                                json=payload, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            print(f"   Answer length: {len(data.get('answer', ''))} chars")
            print(f"   SQL: {data.get('sql', 'None')}")
            print(f"   CSV URL: {data.get('csv_url', 'None')}")
            print(f"   Success: {data.get('success', False)}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False

def test_chat_sse():
    """Test the SSE chat endpoint"""
    print("\n3. Testing chat_sse endpoint (POST /api/vanna/v2/chat_sse):")
    
    payload = {
        "message": "What tables are in the database?",
        "headers": {
            "x-user-id": "sse_user",
            "x-username": "sse_tester",
            "x-user-groups": "api_users"
        },
        "metadata": {
            "test": "sse"
        }
    }
    
    print(f"   POST http://localhost:8000/api/vanna/v2/chat_sse")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post("http://localhost:8000/api/vanna/v2/chat_sse", 
                                json=payload, timeout=30, stream=True)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200 and 'text/event-stream' in response.headers.get('content-type', ''):
            print("   ✓ SSE stream started successfully")
            
            # Read a few events from the stream
            event_count = 0
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data:'):
                        event_data = json.loads(line[5:].strip())
                        event_type = event_data.get('event', 'unknown')
                        print(f"   Event: {event_type}")
                        event_count += 1
                        
                        if event_type == 'complete':
                            print(f"     Answer: {len(event_data.get('answer', ''))} chars")
                            print(f"     SQL: {event_data.get('sql', 'None')}")
                            print(f"     CSV URL: {event_data.get('csv_url', 'None')}")
                            break
                        
                        if event_count >= 5:  # Limit events for demo
                            print("   (Showing first 5 events)")
                            response.close()
                            break
            
            return True
        else:
            print(f"   Error or wrong content type: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False

async def test_websocket():
    """Test the WebSocket chat endpoint"""
    print("\n4. Testing chat_websocket endpoint (WS /api/vanna/v2/chat_websocket):")
    
    try:
        async with websockets.connect("ws://localhost:8000/api/vanna/v2/chat_websocket") as websocket:
            print("   ✓ WebSocket connected")
            
            # Send a message
            message = {
                "message": "List all tables",
                "headers": {
                    "x-user-id": "ws_user",
                    "x-username": "ws_tester",
                    "x-user-groups": "api_users"
                },
                "metadata": {
                    "test": "websocket"
                }
            }
            
            await websocket.send(json.dumps(message))
            print("   Message sent")
            
            # Receive responses
            event_count = 0
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                event_type = data.get('event', 'unknown')
                print(f"   Event: {event_type}")
                
                if event_type == 'complete':
                    print(f"     Answer: {len(data.get('answer', ''))} chars")
                    print(f"     SQL: {data.get('sql', 'None')}")
                    print(f"     CSV URL: {data.get('csv_url', 'None')}")
                    break
                
                event_count += 1
                if event_count >= 5:  # Limit events for demo
                    print("   (Showing first 5 events)")
                    break
            
            return True
    except Exception as e:
        print(f"   Exception: {e}")
        return False

def run_websocket_test():
    """Run WebSocket test in event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(test_websocket())

def main():
    """Main test function"""
    print("=" * 70)
    print("VANNA API V2 ENDPOINTS TEST")
    print("=" * 70)
    
    # Start server
    server_process = start_server()
    
    try:
        # Run tests
        tests_passed = 0
        tests_total = 4
        
        if test_health_endpoints():
            tests_passed += 1
        
        if test_chat_poll():
            tests_passed += 1
        
        if test_chat_sse():
            tests_passed += 1
        
        if run_websocket_test():
            tests_passed += 1
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"\nTests passed: {tests_passed}/{tests_total}")
        
        if tests_passed == tests_total:
            print("✅ All tests passed!")
        else:
            print("⚠️  Some tests failed")
        
        # Show available endpoints
        print("\nAvailable endpoints:")
        print("  GET  /health                    - Root health check")
        print("  GET  /api/v1/health             - V1 health check")
        print("  GET  /api/v1/learning/stats     - Learning statistics")
        print("  POST /api/v1/train              - Training endpoint")
        print("  POST /api/vanna/v2/chat_sse     - SSE streaming chat")
        print("  WS   /api/vanna/v2/chat_websocket - WebSocket chat")
        print("  POST /api/vanna/v2/chat_poll    - Polling chat")
        
        return tests_passed == tests_total
        
    finally:
        # Clean up
        print("\nCleaning up...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Test complete")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
