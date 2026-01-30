#!/bin/bash

# Curl command to test the SSE endpoint
echo "Testing SSE endpoint with curl..."
echo ""

# Curl command for SSE endpoint testing
curl -X POST http://localhost:8001/api/vanna/v2/chat_sse \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Show me all customers",
    "conversation_id": "test-sse-curl-123",
    "headers": {
      "x-user-id": "curl_test_user",
      "x-conversation-id": "test-sse-curl-123",
      "x-username": "curl_tester"
    }
  }' \
  --no-buffer

echo ""
echo "Note: The --no-buffer flag ensures curl displays events as they arrive."
echo "Press Ctrl+C to stop the stream."

# Alternative command with better formatting
echo ""
echo "Alternative command with line-by-line processing:"
echo "curl -X POST http://localhost:8001/api/vanna/v2/chat_sse \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Accept: text/event-stream\" \\"
echo "  -d '{\"message\": \"Show me all customers\", \"conversation_id\": \"test-sse-curl-123\"}' \\"
echo "  -N"

# Simple test command (one-liner)
echo ""
echo "Simple one-liner test:"
echo "curl -s -X POST http://localhost:8001/api/vanna/v2/chat_sse -H \"Content-Type: application/json\" -H \"Accept: text/event-stream\" -d '{\"message\":\"Show me all customers\"}' -N | while read -r line; do echo \"\$line\"; done"