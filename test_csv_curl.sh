#!/bin/bash

# Test the chat_poll endpoint with curl
echo "Testing CSV URL capture with curl..."
echo "======================================"

# Make the API request
echo "Making POST request to /api/vanna/v2/chat_poll..."
curl -X POST http://localhost:8001/api/vanna/v2/chat_poll \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all customers",
    "headers": {
      "x-user-id": "curl_test_user",
      "x-conversation-id": "curl_test_conv"
    }
  }' \
  --silent | jq '{
    answer_length: (.answer | length),
    sql: .sql,
    csv_url: .csv_url,
    success: .success,
    tool_used: .tool_used,
    chart_generated: .chart_generated
  }'

echo ""
echo "======================================"
echo "If csv_url is not null, the fix is working!"
echo ""

# If you want to test the CSV file directly, you can extract the URL and test it:
echo "To test the CSV file directly, run:"
echo "curl -s http://localhost:8001\$(curl -s -X POST http://localhost:8001/api/vanna/v2/chat_poll -H 'Content-Type: application/json' -d '{\"message\":\"Show me all customers\",\"headers\":{\"x-user-id\":\"test\",\"x-conversation-id\":\"test\"}}' | jq -r '.csv_url') | head -5"