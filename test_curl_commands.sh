#!/bin/bash

# Vanna AI API Test Curl Commands
# This script contains curl commands to test the /chat endpoint
# Make sure the API server is running on localhost:8001

echo "Vanna AI API Test Commands"
echo "=========================="
echo ""

# Test 1: Basic health check
echo "1. Testing API health:"
echo "----------------------"
curl -X GET http://localhost:8001/health
echo ""
echo ""

# Test 2: Simple chat request with conversation ID
echo "2. Simple chat request with conversation ID:"
echo "--------------------------------------------"
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user_001" \
  -H "x-username: Test User" \
  -H "x-user-groups: api_users" \
  -H "x-conversation-id: conv_001" \
  -d '{
    "message": "Show me all tables in the database",
    "headers": {
      "x-conversation-id": "conv_001"
    }
  }'
echo ""
echo ""

# Test 3: Chat with different conversation ID for isolation
echo "3. Chat with different conversation ID (isolated context):"
echo "----------------------------------------------------------"
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user_001" \
  -H "x-username: Test User" \
  -H "x-user-groups: api_users" \
  -H "x-conversation-id: sales_analysis" \
  -d '{
    "message": "What are the top 5 products by sales?",
    "headers": {
      "x-conversation-id": "sales_analysis"
    },
    "metadata": {
      "department": "sales",
      "priority": "high"
    }
  }'
echo ""
echo ""

# Test 4: Chat with SSE (Server-Sent Events) streaming
echo "4. Chat with SSE streaming (real-time response):"
echo "------------------------------------------------"
echo "Note: This command shows the streaming response format"
curl -X POST http://localhost:8001/api/vanna/v2/chat_sse \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user_002" \
  -H "x-username: Streaming User" \
  -H "x-user-groups: api_users" \
  -H "x-conversation-id: streaming_test" \
  -d '{
    "message": "Tell me about the database structure",
    "headers": {
      "x-conversation-id": "streaming_test"
    }
  }'
echo ""
echo ""

# Test 5: Chat with polling endpoint (v2)
echo "5. Chat with polling endpoint (v2):"
echo "-----------------------------------"
curl -X POST http://localhost:8001/api/vanna/v2/chat_poll \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user_003" \
  -H "x-username: Polling User" \
  -H "x-user-groups: api_users" \
  -H "x-conversation-id: poll_test_001" \
  -d '{
    "message": "How many customers do we have?",
    "headers": {
      "x-conversation-id": "poll_test_001"
    }
  }'
echo ""
echo ""

# Test 6: Chat without conversation ID (uses default)
echo "6. Chat without conversation ID (uses default):"
echo "-----------------------------------------------"
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user_004" \
  -H "x-username: Default User" \
  -H "x-user-groups: api_users" \
  -d '{
    "message": "What is the average order value?"
  }'
echo ""
echo ""

# Test 7: Chat with complex question and conversation context
echo "7. Complex question with conversation context:"
echo "----------------------------------------------"
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: analyst_001" \
  -H "x-username: Data Analyst" \
  -H "x-user-groups: api_users,analysts" \
  -H "x-conversation-id: quarterly_report_2024_q1" \
  -d '{
    "message": "Show me monthly sales trends for the last 6 months broken down by product category",
    "headers": {
      "x-conversation-id": "quarterly_report_2024_q1"
    },
    "metadata": {
      "report_type": "quarterly",
      "timeframe": "6_months",
      "breakdown": "product_category"
    }
  }'
echo ""
echo ""

# Test 8: Get conversation history for a specific conversation ID
echo "8. Get conversation history for specific conversation ID:"
echo "----------------------------------------------------------"
curl -X GET "http://localhost:8001/api/v1/conversation/history?user_identifier=analyst_001&conversation_id=quarterly_report_2024_q1&limit=5"
echo ""
echo ""

# Test 9: Error case - missing message
echo "9. Error case - missing message:"
echo "--------------------------------"
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: test_user_001" \
  -H "x-user-groups: api_users" \
  -H "x-conversation-id: error_test" \
  -d '{
    "headers": {
      "x-conversation-id": "error_test"
    }
  }'
echo ""
echo ""

# Test 10: Test learning enhancement
echo "10. Test learning enhancement:"
echo "------------------------------"
curl -X POST http://localhost:8001/api/v1/learning/enhance_test \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me customer orders from last week"
  }'
echo ""
echo ""

echo "All test commands completed!"
echo ""
echo "Quick reference for testing /chat endpoint:"
echo "=========================================="
echo ""
echo "Basic format:"
echo 'curl -X POST http://localhost:8001/api/v1/chat \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "x-user-id: YOUR_USER_ID" \'
echo '  -H "x-user-groups: api_users" \'
echo '  -H "x-conversation-id: YOUR_CONVERSATION_ID" \'
echo '  -d '\''{'
echo '    "message": "YOUR_QUESTION_HERE",'
echo '    "headers": {'
echo '      "x-conversation-id": "YOUR_CONVERSATION_ID"'
echo '    }'
echo '  }'\'''
echo ""
echo "Alternative endpoints:"
echo "- /api/vanna/v2/chat_sse (Server-Sent Events streaming)"
echo "- /api/vanna/v2/chat_poll (Polling with v2 enhancements)"
echo "- /api/vanna/v2/chat_websocket (WebSocket - not shown in curl)"
echo ""
echo "Note: The API server must be running on localhost:8001"
echo "Start it with: python api.py  or  uvicorn api:app --host 0.0.0.0 --port 8001"