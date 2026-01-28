#!/usr/bin/env python3
"""
Test script to verify CSV URL capture in SSE endpoint.
"""
import asyncio
import json
import httpx
import sys
import time

async def test_sse_csv_capture():
    """Test the SSE endpoint with a query that should generate CSV"""
    url = "http://localhost:8001/api/vanna/v2/chat_sse"
    
    # Test query that should generate CSV
    test_queries = [
        "Show me all customers",
        "List all orders",
        "Show me the top 10 products"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing query: {query}")
        print(f"{'='*60}")
        
        payload = {
            "message": query,
            "headers": {
                "x-user-id": "test_user",
                "x-conversation-id": "test_conversation"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Make SSE request
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Accept": "text/event-stream"}
                )
                
                if response.status_code != 200:
                    print(f"Error: Status {response.status_code}")
                    print(f"Response: {response.text}")
                    continue
                
                # Parse SSE events
                csv_url = None
                sql_query = None
                answer = None
                
                lines = response.text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            event_type = data.get('event')
                            
                            if event_type == 'csv':
                                csv_url = data.get('url')
                                print(f"✓ CSV event received: {csv_url}")
                            elif event_type == 'sql':
                                sql_query = data.get('sql')
                                print(f"✓ SQL event received: {sql_query[:100]}..." if sql_query and len(sql_query) > 100 else f"✓ SQL event received: {sql_query}")
                            elif event_type == 'complete':
                                answer = data.get('answer', '')[:200]
                                complete_csv_url = data.get('csv_url')
                                print(f"✓ Complete event received")
                                print(f"  Answer preview: {answer}...")
                                print(f"  CSV URL in complete event: {complete_csv_url}")
                                
                                # Check if CSV URL is present
                                if complete_csv_url:
                                    print(f"✅ SUCCESS: CSV URL captured: {complete_csv_url}")
                                else:
                                    print(f"❌ FAILURE: CSV URL is null in complete event")
                                    print(f"  Note: CSV event URL was: {csv_url}")
                        except json.JSONDecodeError as e:
                            print(f"  JSON decode error: {e}")
                            continue
                
                # Also test the polling endpoint
                print(f"\nTesting polling endpoint for same query...")
                poll_url = "http://localhost:8001/api/vanna/v2/chat_poll"
                poll_response = await client.post(poll_url, json=payload)
                
                if poll_response.status_code == 200:
                    poll_data = poll_response.json()
                    poll_csv_url = poll_data.get('csv_url')
                    print(f"Poll response CSV URL: {poll_csv_url}")
                    if poll_csv_url:
                        print(f"✅ Poll endpoint CSV URL: {poll_csv_url}")
                    else:
                        print(f"❌ Poll endpoint CSV URL is null")
                else:
                    print(f"Poll endpoint error: {poll_response.status_code}")
                    print(f"Poll response: {poll_response.text}")
                
        except Exception as e:
            print(f"Error testing query '{query}': {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between tests
        await asyncio.sleep(2)

async def main():
    """Main test function"""
    print("Testing CSV URL capture in Vanna AI API")
    print("Make sure the server is running on localhost:8001")
    print()
    
    try:
        await test_sse_csv_capture()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)