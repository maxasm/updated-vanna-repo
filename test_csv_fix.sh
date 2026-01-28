#!/bin/bash

echo "Testing CSV URL Fix Implementation"
echo "=================================="
echo ""
echo "This script tests that:"
echo "1. CSV URLs are not null when CSV files are generated"
echo "2. SQL is returned in responses"
echo "3. Both polling and SSE endpoints work correctly"
echo ""

# Test 1: Polling endpoint (should return JSON with SQL and CSV URL)
echo "Test 1: Testing polling endpoint (/api/vanna/v2/chat_poll)"
echo "----------------------------------------------------------"
curl -X POST http://localhost:8001/api/vanna/v2/chat_poll \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all customers",
    "headers": {
      "x-user-id": "test_user_123",
      "x-conversation-id": "test_convo_456",
      "x-username": "Test User"
    },
    "metadata": {
      "test": true
    }
  }' 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('✓ Response received successfully')
    print(f'  Answer length: {len(data.get(\"answer\", \"\"))} characters')
    print(f'  SQL present: {\"sql\" in data and data[\"sql\"]}')
    if data.get('sql'):
        print(f'  SQL preview: {data[\"sql\"][:100]}...')
    print(f'  CSV URL: {data.get(\"csv_url\", \"NOT FOUND\")}')
    print(f'  Success: {data.get(\"success\", False)}')
    print(f'  Tool used: {data.get(\"tool_used\", False)}')
    
    # Check if CSV URL is not null (the main fix)
    if data.get('csv_url'):
        print('✅ CSV URL is NOT null - FIX IS WORKING!')
    else:
        print('❌ CSV URL is null - fix may not be working')
        
except Exception as e:
    print(f'Error: {e}')
"
echo ""

# Test 2: SSE endpoint (streaming - should show events including SQL)
echo "Test 2: Testing SSE endpoint (/api/vanna/v2/chat_sse)"
echo "------------------------------------------------------"
echo "Note: This will stream events for 5 seconds then exit"
echo "Looking for 'event: sql' and 'event: csv' events"
echo ""

timeout 5 curl -X POST http://localhost:8001/api/vanna/v2/chat_sse \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Show me recent orders",
    "headers": {
      "x-user-id": "test_user_123",
      "x-conversation-id": "test_convo_456",
      "x-username": "Test User"
    },
    "metadata": {
      "test": true
    }
  }' 2>/dev/null | grep -E "(event:|data:)" | head -20

echo ""
echo "Test 3: Quick health check"
echo "--------------------------"
curl -s http://localhost:8001/health | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data.get(\"status\", \"unknown\")}')
print(f'Service: {data.get(\"service\", \"unknown\")}')
"

echo ""
echo "=================================="
echo "Test Summary:"
echo "- Polling endpoint should return SQL and CSV URL"
echo "- SSE endpoint should stream 'sql' and 'csv' events"
echo "- CSV URL should NOT be null when CSV is generated"
echo ""
echo "To manually test with more detail:"
echo "  curl -X POST http://localhost:8001/api/vanna/v2/chat_poll \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"message\": \"Show me all customers\", \"headers\": {\"x-user-id\": \"test\"}}' | jq"
echo ""
echo "To test SSE streaming:"
echo "  curl -X POST http://localhost:8001/api/vanna/v2/chat_sse \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -H \"Accept: text/event-stream\" \\"
echo "    -d '{\"message\": \"Show me all customers\", \"headers\": {\"x-user-id\": \"test\"}}'"