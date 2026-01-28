#!/usr/bin/env python3
"""
Simple test to check CSV URL capture
"""
import json
import httpx
import asyncio

async def test_csv_capture():
    """Test CSV capture with a simple query"""
    url = "http://localhost:8001/api/vanna/v2/chat_poll"
    
    # Simple query that should generate CSV
    payload = {
        "message": "Show me all customers",
        "headers": {
            "x-user-id": "test_user_123",
            "x-conversation-id": "test_conv_456"
        }
    }
    
    print("Testing CSV URL capture...")
    print(f"Query: {payload['message']}")
    print(f"URL: {url}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nResponse status: {response.status_code}")
                print(f"Answer preview: {data.get('answer', '')[:200]}...")
                print(f"SQL: {data.get('sql', '')[:100]}..." if data.get('sql') else "SQL: None")
                print(f"CSV URL: {data.get('csv_url', 'None')}")
                print(f"Success: {data.get('success', 'Not specified')}")
                print(f"Tool used: {data.get('tool_used', 'Not specified')}")
                
                if data.get('csv_url'):
                    print("\n✅ SUCCESS: CSV URL captured!")
                    print(f"   CSV URL: {data['csv_url']}")
                    
                    # Test if the CSV file is accessible
                    csv_url = data['csv_url']
                    if csv_url.startswith('/'):
                        csv_url = f"http://localhost:8001{csv_url}"
                    
                    try:
                        csv_response = await client.get(csv_url, timeout=10.0)
                        if csv_response.status_code == 200:
                            print(f"✅ CSV file is accessible at: {csv_url}")
                            # Show first few lines of CSV
                            csv_content = csv_response.text
                            lines = csv_content.split('\n')
                            print(f"   CSV preview (first 3 lines):")
                            for i, line in enumerate(lines[:3]):
                                if line.strip():
                                    print(f"   {i+1}: {line[:100]}..." if len(line) > 100 else f"   {i+1}: {line}")
                        else:
                            print(f"⚠️  CSV file not accessible: Status {csv_response.status_code}")
                    except Exception as e:
                        print(f"⚠️  Error accessing CSV file: {e}")
                else:
                    print("\n❌ FAILURE: CSV URL is null")
                    
                    # Check if there's any error or warning in response
                    if 'error' in data:
                        print(f"   Error: {data['error']}")
                    
            else:
                print(f"\n❌ Error: Status {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the test"""
    print("=" * 60)
    print("Testing CSV URL capture in Vanna AI API")
    print("=" * 60)
    
    await test_csv_capture()
    
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())