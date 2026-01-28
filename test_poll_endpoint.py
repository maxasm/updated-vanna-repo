#!/usr/bin/env python3
"""
Test the chat_poll endpoint directly
"""
import json
import httpx
import asyncio

async def test_poll_endpoint():
    """Test the chat_poll endpoint"""
    url = "http://localhost:8001/api/vanna/v2/chat_poll"
    
    payload = {
        "message": "Show me all customers",
        "headers": {
            "x-user-id": "test_user",
            "x-conversation-id": "test_conv"
        }
    }
    
    print(f"Testing {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            
            print(f"\nStatus: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            try:
                data = response.json()
                print(f"\nResponse JSON:")
                print(json.dumps(data, indent=2))
                
                # Check if it has the expected structure
                if 'answer' in data:
                    print(f"\n✅ Has 'answer' field: {data['answer'][:100]}...")
                if 'sql' in data:
                    print(f"✅ Has 'sql' field: {data['sql'][:100] if data['sql'] else 'None'}...")
                if 'csv_url' in data:
                    print(f"✅ Has 'csv_url' field: {data['csv_url']}")
                if 'chunks' in data:
                    print(f"⚠️  Has 'chunks' field (list of {len(data['chunks'])} chunks)")
                    
            except Exception as e:
                print(f"\nError parsing JSON: {e}")
                print(f"Raw response: {response.text[:500]}...")
                
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the test"""
    print("=" * 80)
    print("Testing chat_poll endpoint")
    print("=" * 80)
    
    await test_poll_endpoint()
    
    print("\n" + "=" * 80)
    print("Test complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())