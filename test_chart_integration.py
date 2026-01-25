import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
import json
import asyncio
from api import EnhancedChatHandler, CSVResultManager, ConversationStore, ConversationContextEnhancer

class TestChartIntegration(unittest.TestCase):
    def setUp(self):
        self.agent = MagicMock()
        self.learning_manager = MagicMock()
        self.learning_manager.record_tool_usage = AsyncMock()
        self.learning_manager.enhance_question_with_learned_patterns = MagicMock(return_value="enhanced question")
        
        self.csv_manager = MagicMock()
        self.csv_manager.get_csv_url.return_value = "/static/test.csv"
        
        self.sql_runner = MagicMock()
        
        self.conversation_store = MagicMock()
        self.conversation_store.save_conversation_turn = AsyncMock()
        
        self.conversation_enhancer = MagicMock()
        self.conversation_enhancer.enhance_question_with_context = AsyncMock(return_value="enhanced question")
        
        self.handler = EnhancedChatHandler(
            agent=self.agent,
            learning_manager=self.learning_manager,
            csv_manager=self.csv_manager,
            sql_runner=self.sql_runner,
            conversation_store=self.conversation_store,
            conversation_enhancer=self.conversation_enhancer
        )

    def test_handle_chat_request_with_chart(self):
        # Mock request
        request = {
            "message": "Show me sales",
            "headers": {"x-user-id": "test"}
        }
        
        # Mock agent response with SQL tool call
        tool_call = MagicMock()
        tool_call.tool_call_component.tool_name = "run_sql"
        tool_call.tool_call_component.args = {"sql": "SELECT * FROM sales"}
        
        # Mock async generator for agent.send_message
        async def mock_send_message(*args, **kwargs):
            yield tool_call
            
        self.agent.send_message = mock_send_message
        
        # Mock SQL runner returning a dataframe
        df = pd.DataFrame({'Category': ['A', 'B'], 'Value': [10, 20]})
        self.sql_runner.run_sql.return_value = df
        
        # Mock chart generator
        # We need to rely on the real PlotlyChartGenerator instantiated in handler
        # But for this test, let's verify it gets called or the result is in response
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.handler.handle_chat_request(request))
        
        print("Response keys:", response.keys())
        if 'chart' in response:
            print("Chart field present:", bool(response['chart']))
            # If chart is generated, it should be a dict or string
            if response['chart']:
                print("Chart content type:", type(response['chart']))
        else:
            print("Chart field MISSING")
            
        self.assertTrue('chart' in response)
        # We expect a chart because we have simple categorical/numerical data
        self.assertIsNotNone(response['chart'])

if __name__ == "__main__":
    unittest.main()
