#!/bin/bash

# Simple curl command to test CSV URL capture
echo "Testing CSV URL capture with a simple curl command..."
echo ""

# Single curl command that shows the CSV URL
curl -s -X POST http://localhost:8001/api/vanna/v2/chat_poll \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all customers",
    "headers": {
      "x-user-id": "simple_test",
      "x-conversation-id": "simple_test"
    }
  }' | jq '{csv_url: .csv_url, success: .success}'

echo ""
echo "If csv_url is not null, the bug is fixed!"