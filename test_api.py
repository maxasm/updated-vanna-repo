#!/usr/bin/env python3
"""Test script for the Vanna AI REST API"""

import asyncio
import aiohttp
import json
import time
import sys
import subprocess
import os
from pathlib import Path

async def test_api():
    """Test the API endpoints"""
    
    # Start the API server in background
    print("🚀 Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": "."}
    )
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    try:
        async with aiohttp.ClientSession() as session:
            host = os.getenv("HOST", "localhost")
            port = os.getenv("PORT", "8001")
            base_url = f"http://{host}:{port}"
            
            # Test health endpoint
            print("\n🧪 Testing health endpoint...")
            try:
                async with session.get(f"{base_url}/api/v1/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Health check: {data}")
                    else:
                        print(f"❌ Health check failed: {response.status}")
            except Exception as e:
                print(f"❌ Health check error: {e}")
            
            # Test learning stats endpoint
            print("\n🧪 Testing learning stats endpoint...")
            try:
                async with session.get(f"{base_url}/api/v1/learning/stats") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Learning stats: {data}")
                    else:
                        print(f"❌ Learning stats failed: {response.status}")
            except Exception as e:
                print(f"❌ Learning stats error: {e}")
            
            # Test chat endpoint with a simple query
            print("\n🧪 Testing chat endpoint...")
            test_queries = [
                "Show me all tables in the database",
                "How many customers are there?",
                "What are the top 5 products by sales?"
            ]
            
            for query in test_queries:
                print(f"\n📝 Testing query: '{query}'")
                try:
                    payload = {
                        "message": query,
                        "headers": {
                            "x-user-id": "test_user",
                            "x-username": "tester",
                            "x-user-groups": "api_users"
                        },
                        "metadata": {
                            "test": True,
                            "query_type": "test"
                        }
                    }
                    
                    async with session.post(f"{base_url}/api/v1/chat", json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"✅ Chat response received")
                            print(f"   Answer length: {len(data.get('answer', ''))} chars")
                            print(f"   SQL: {data.get('sql', 'None')[:100]}..." if data.get('sql') else "   SQL: None")
                            print(f"   CSV URL: {data.get('csv_url', 'None')}")
                            print(f"   Success: {data.get('success', False)}")
                            
                            # If CSV URL is provided, test downloading it
                            csv_url = data.get('csv_url')
                            if csv_url:
                                try:
                                    async with session.get(f"{base_url}{csv_url}") as csv_response:
                                        if csv_response.status == 200:
                                            csv_content = await csv_response.text()
                                            print(f"✅ CSV downloaded ({len(csv_content)} bytes)")
                                        else:
                                            print(f"⚠️  CSV download failed: {csv_response.status}")
                                except Exception as e:
                                    print(f"⚠️  CSV download error: {e}")
                        else:
                            print(f"❌ Chat request failed: {response.status}")
                            error_text = await response.text()
                            print(f"   Error: {error_text[:200]}")
                except Exception as e:
                    print(f"❌ Chat request error: {e}")
            
            # Test the base Vanna endpoints (from VannaFastAPIServer)
            print("\n🧪 Testing base Vanna endpoints...")
            try:
                # Test the root endpoint (should return HTML)
                async with session.get(f"{base_url}/") as response:
                    if response.status == 200:
                        content = await response.text()
                        if "<html" in content.lower() or "<!doctype" in content.lower():
                            print("✅ Root endpoint returns HTML interface")
                        else:
                            print(f"⚠️  Root endpoint returned non-HTML: {content[:100]}...")
                    else:
                        print(f"❌ Root endpoint failed: {response.status}")
            except Exception as e:
                print(f"❌ Root endpoint error: {e}")
            
    finally:
        # Kill the API server
        print("\n🛑 Stopping API server...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
        
        stdout, stderr = api_process.communicate()
        if stdout:
            print(f"Server stdout: {stdout.decode()[:500]}...")
        if stderr:
            print(f"Server stderr: {stderr.decode()[:500]}...")
        
        print("✅ API server stopped")

if __name__ == "__main__":
    # Check if required modules are installed
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp
    
    # Run the test
    asyncio.run(test_api())
