#!/usr/bin/env python3
"""
Detailed test to debug CSV URL capture
"""
import json
import httpx
import asyncio
import sys

async def test_detailed_csv():
    """Test CSV capture with detailed debugging"""
    url = "http://localhost:8001/api/vanna/v2/chat_poll"
    
    # Test query
    payload = {
        "message": "Show me all customers",
        "headers": {
            "x-user-id": "debug_user",
            "x-conversation-id": "debug_conv"
        }
    }
    
    print("Testing CSV URL capture with detailed debugging...")
    print(f"Query: {payload['message']}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n=== RESPONSE DATA ===")
                print(f"Status: {response.status_code}")
                print(f"Answer length: {len(data.get('answer', ''))}")
                print(f"Answer preview: {data.get('answer', '')[:500]}...")
                print(f"SQL: {data.get('sql', 'None')}")
                print(f"CSV URL: {data.get('csv_url', 'None')}")
                print(f"Success: {data.get('success', 'Not specified')}")
                print(f"Tool used: {data.get('tool_used', 'Not specified')}")
                print(f"Chart generated: {data.get('chart_generated', 'Not specified')}")
                print(f"Chart source: {data.get('chart_source', 'Not specified')}")
                
                # Check for any errors
                if 'error' in data:
                    print(f"Error in response: {data['error']}")
                
                # Check if we have chart info
                if data.get('chart_info'):
                    print(f"Chart info: {json.dumps(data['chart_info'], indent=2)}")
                
                # Check the full response for debugging
                print(f"\n=== FULL RESPONSE KEYS ===")
                for key in data.keys():
                    print(f"  - {key}: {type(data[key])}")
                
                # If CSV URL is present, test it
                csv_url = data.get('csv_url')
                if csv_url:
                    print(f"\n✅ CSV URL captured: {csv_url}")
                    
                    # Make sure URL is absolute
                    if csv_url.startswith('/'):
                        csv_url = f"http://localhost:8001{csv_url}"
                    
                    try:
                        csv_response = await client.get(csv_url, timeout=10.0)
                        if csv_response.status_code == 200:
                            print(f"✅ CSV file is accessible")
                            csv_content = csv_response.text
                            lines = csv_content.split('\n')
                            print(f"   CSV has {len(lines)} lines, {len(lines[0].split(','))} columns")
                            print(f"   First 2 lines:")
                            for i, line in enumerate(lines[:2]):
                                if line.strip():
                                    print(f"   {i+1}: {line[:100]}..." if len(line) > 100 else f"   {i+1}: {line}")
                        else:
                            print(f"❌ CSV file not accessible: Status {csv_response.status_code}")
                            print(f"   Response: {csv_response.text[:200]}")
                    except Exception as e:
                        print(f"❌ Error accessing CSV file: {e}")
                else:
                    print(f"\n❌ CSV URL is null")
                    
                    # Try to find recent CSV files
                    print(f"\n=== CHECKING FOR RECENT CSV FILES ===")
                    try:
                        # Check health endpoint
                        health_response = await client.get("http://localhost:8001/health", timeout=5.0)
                        if health_response.status_code == 200:
                            print(f"Server health: OK")
                    except Exception as e:
                        print(f"Health check error: {e}")
                
            else:
                print(f"\n❌ Error: Status {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the test"""
    print("=" * 80)
    print("Detailed CSV URL capture test")
    print("=" * 80)
    
    await test_detailed_csv()
    
    print("\n" + "=" * 80)
    print("Test complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())