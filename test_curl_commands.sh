#!/bin/bash
# Test curl commands for Vanna AI REST API

echo "=========================================="
echo "Vanna AI REST API - Test Curl Commands"
echo "=========================================="
echo ""
echo "Make sure the API server is running:"
echo "  python api.py"
echo ""
echo "Or start it in background:"
echo "  python api.py &"
echo ""
echo "Wait for server to start, then run these tests:"
echo ""

# Base URL
HOST="${HOST:-localhost}"
PORT="${PORT:-8001}"
BASE_URL="http://${HOST}:${PORT}"

echo "1. Test health endpoint:"
echo "curl -s $BASE_URL/api/v1/health | python3 -m json.tool"
echo ""
curl -s $BASE_URL/api/v1/health | python3 -m json.tool 2>/dev/null || echo "Server not running or error"
echo ""

echo "2. Test learning statistics:"
echo "curl -s $BASE_URL/api/v1/learning/stats | python3 -m json.tool"
echo ""
curl -s $BASE_URL/api/v1/learning/stats | python3 -m json.tool 2>/dev/null || echo "Server not running or error"
echo ""

echo "3. Test chat endpoint with simple query:"
echo "curl -s -X POST $BASE_URL/api/v1/chat \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\": \"How many customers are there?\", \"headers\": {\"x-user-id\": \"test_user\", \"x-username\": \"tester\", \"x-user-groups\": \"api_users\"}, \"metadata\": {\"test\": true}}' \\"
echo "  | python3 -m json.tool"
echo ""
curl -s -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many customers are there?", "headers": {"x-user-id": "test_user", "x-username": "tester", "x-user-groups": "api_users"}, "metadata": {"test": true}}' \
  | python3 -m json.tool 2>/dev/null || echo "Server not running or error"
echo ""

echo "4. Test chat endpoint with table listing:"
echo "curl -s -X POST $BASE_URL/api/v1/chat \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\": \"Show me all tables in the database\", \"headers\": {\"x-user-id\": \"test_user\", \"x-username\": \"tester\", \"x-user-groups\": \"api_users\"}, \"metadata\": {\"test\": true}}' \\"
echo "  | python3 -c \"import sys, json; data=json.load(sys.stdin); print('Answer preview:', data.get('answer', '')[:200]); print('SQL:', data.get('sql', 'None')); print('CSV URL:', data.get('csv_url', 'None')); print('Success:', data.get('success', False))\""
echo ""
curl -s -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all tables in the database", "headers": {"x-user-id": "test_user", "x-username": "tester", "x-user-groups": "api_users"}, "metadata": {"test": true}}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer preview:', data.get('answer', '')[:200]); print('SQL:', data.get('sql', 'None')); print('CSV URL:', data.get('csv_url', 'None')); print('Success:', data.get('success', False))" 2>/dev/null || echo "Server not running or error"
echo ""

echo "5. Test chat endpoint with product query:"
echo "curl -s -X POST $BASE_URL/api/v1/chat \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\": \"What are the top 5 most expensive products?\", \"headers\": {\"x-user-id\": \"test_user\", \"x-username\": \"tester\", \"x-user-groups\": \"api_users\"}, \"metadata\": {\"test\": true}}' \\"
echo "  | python3 -c \"import sys, json; data=json.load(sys.stdin); print('Answer length:', len(data.get('answer', ''))); print('Has SQL:', bool(data.get('sql'))); print('Has CSV URL:', bool(data.get('csv_url'))); print('Success:', data.get('success', False))\""
echo ""
curl -s -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top 5 most expensive products?", "headers": {"x-user-id": "test_user", "x-username": "tester", "x-user-groups": "api_users"}, "metadata": {"test": true}}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer length:', len(data.get('answer', ''))); print('Has SQL:', bool(data.get('sql'))); print('Has CSV URL:', bool(data.get('csv_url'))); print('Success:', data.get('success', False))" 2>/dev/null || echo "Server not running or error"
echo ""

echo "6. Test training endpoint:"
echo "curl -s -X POST $BASE_URL/api/v1/train \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{}' \\"
echo "  | python3 -m json.tool"
echo ""
curl -s -X POST $BASE_URL/api/v1/train \
  -H "Content-Type: application/json" \
  -d '{}' \
  | python3 -m json.tool 2>/dev/null || echo "Server not running or error"
echo ""

echo "7. Test web interface (check if HTML is returned):"
echo "curl -s -I $BASE_URL/ | head -5"
echo ""
curl -s -I $BASE_URL/ 2>/dev/null | head -5 || echo "Server not running or error"
echo ""

echo "=========================================="
echo "Quick Test Commands (copy and paste):"
echo "=========================================="
echo ""
echo "# 1. Health check"
echo "curl -s $BASE_URL/api/v1/health"
echo ""
echo "# 2. Learning stats"
echo "curl -s $BASE_URL/api/v1/learning/stats"
echo ""
echo "# 3. Simple chat query"
echo "curl -s -X POST $BASE_URL/api/v1/chat -H \"Content-Type: application/json\" -d '{\"message\": \"How many customers are there?\", \"headers\": {\"x-user-id\": \"test\", \"x-username\": \"tester\", \"x-user-groups\": \"api_users\"}, \"metadata\": {\"test\": true}}'"
echo ""
echo "# 4. Table listing"
echo "curl -s -X POST $BASE_URL/api/v1/chat -H \"Content-Type: application/json\" -d '{\"message\": \"Show me all tables\", \"headers\": {\"x-user-id\": \"test\", \"x-username\": \"tester\", \"x-user-groups\": \"api_users\"}, \"metadata\": {\"test\": true}}'"
echo ""
echo "# 5. With pretty JSON output"
echo "curl -s -X POST $BASE_URL/api/v1/chat -H \"Content-Type: application/json\" -d '{\"message\": \"Show me all tables\"}' | python3 -m json.tool"
echo ""
echo "=========================================="
echo "Note: The API returns the format:"
echo "  - answer: Natural language response"
echo "  - sql: Extracted SQL query (when available)"
echo "  - csv_url: Link to CSV file (when generated)"
echo "  - success: Boolean indicating if query was successful"
echo "  - timestamp: ISO timestamp"
echo "=========================================="
