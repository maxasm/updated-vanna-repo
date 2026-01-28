#!/usr/bin/env python3
"""
Final test to verify CSV URL is accessible
"""
import json
import httpx
import asyncio

async def test_csv_url():
    """Test that CSV URL is accessible"""
    url = "http://localhost:8001/api/vanna/v2/chat_poll"
    
    payload = {
        "message": "Show me all customers",
        "headers": {
            "x-user-id": "test_user_final",
            "x-conversation-id": "test_conv_final"
        }
    }
    
    print(f"Testing {url}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            
            print(f"\nStatus: {response.status_code}")
            
            data = response.json()
            
            # Check if we have a CSV URL
            csv_url = data.get('csv_url')
            if csv_url:
                print(f"\n✅ CSV URL found: {csv_url}")
                
                # Test if the CSV file is accessible
                csv_full_url = f"http://localhost:8001{csv_url}"
                print(f"Testing CSV accessibility: {csv_full_url}")
                
                csv_response = await client.get(csv_full_url)
                if csv_response.status_code == 200:
                    print(f"✅ CSV file is accessible (size: {len(csv_response.content)} bytes)")
                    
                    # Check if it's a valid CSV
                    content = csv_response.text
                    lines = content.split('\n')
                    if len(lines) > 1:
                        print(f"✅ CSV has {len(lines)} lines, {len(lines[0].split(','))} columns")
                        print(f"First line: {lines[0][:100]}...")
                    else:
                        print(f"⚠️  CSV appears empty or invalid")
                else:
                    print(f"❌ CSV file not accessible: {csv_response.status_code}")
            else:
                print(f"\n❌ No CSV URL in response")
                print(f"Response keys: {list(data.keys())}")
                
            # Print summary
            print(f"\n📊 Response summary:")
            print(f"  - Answer length: {len(data.get('answer', ''))} chars")
            print(f"  - SQL: {data.get('sql', 'None')}")
            print(f"  - CSV URL: {data.get('csv_url', 'None')}")
            print(f"  - Success: {data.get('success', 'Unknown')}")
            print(f"  - Tool used: {data.get('tool_used', 'Unknown')}")
            print(f"  - Chart generated: {data.get('chart_generated', 'Unknown')}")
                
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run the test"""
    print("=" * 80)
    print("Final CSV URL verification test")
    print("=" * 80)
    
    await test_csv_url()
    
    print("\n" + "=" * 80)
    print("Test complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())