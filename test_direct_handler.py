import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

# Add current directory to path to import from api.py
sys.path.insert(0, str(Path(__file__).parent))

from api import EnhancedChatHandler, CSVResultManager, ConversationStore, ConversationContextEnhancer
from learning_manager import LearningManager
from vanna.integrations.mysql import MySQLRunner
from dotenv import load_dotenv

load_dotenv()

async def test_handler_with_mock_agent():
    """Test EnhancedChatHandler with a mock agent that simulates tool calls"""
    
    print("Testing EnhancedChatHandler with mock agent...")
    
    # Create a mock agent that yields components similar to what Vanna agent yields
    class MockComponent:
        def __init__(self, has_simple_text=None, has_tool_call=None, has_tool_result=None):
            self.simple_component = None
            self.tool_call_component = None
            self.tool_result_component = None
            
            if has_simple_text:
                self.simple_component = MagicMock()
                self.simple_component.text = has_simple_text
            
            if has_tool_call:
                self.tool_call_component = MagicMock()
                self.tool_call_component.tool_name = has_tool_call.get('tool_name')
                self.tool_call_component.args = has_tool_call.get('args', {})
            
            if has_tool_result:
                self.tool_result_component = MagicMock()
                self.tool_result_component.error = has_tool_result.get('error')
    
    # Create mock agent with async iterator
    mock_agent = MagicMock()
    
    # Simulate what happens when agent runs a successful query
    # First component: text saying what it will do
    component1 = MockComponent(has_simple_text="I'll execute a query to show all tables in the database.")
    
    # Second component: tool call for run_sql
    component2 = MockComponent(has_tool_call={
        'tool_name': 'run_sql',
        'args': {'sql': "SELECT table_name FROM information_schema.tables WHERE table_schema = 'mapa_db'"}
    })
    
    # Third component: text with results
    component3 = MockComponent(has_simple_text="Here are the tables:\nTABLE_SCHEMA,TABLE_NAME\nmapa_db,aankoop\n...\nResults saved to file: query_results_abc123.csv")
    
    # Create async iterator
    async def mock_send_message(*args, **kwargs):
        for component in [component1, component2, component3]:
            yield component
    
    mock_agent.send_message = mock_send_message
    
    # Create mock SQL runner that returns a dataframe
    mock_sql_runner = MagicMock()
    mock_df = pd.DataFrame({
        'TABLE_SCHEMA': ['mapa_db', 'mapa_db'],
        'TABLE_NAME': ['aankoop', 'another_table']
    })
    mock_sql_runner.run_sql.return_value = mock_df
    
    # Create other mocks
    mock_learning_manager = MagicMock()
    mock_learning_manager.enhance_question_with_learned_patterns.return_value = "Show me all tables"
    
    csv_manager = CSVResultManager()
    conversation_store = ConversationStore()
    conversation_enhancer = ConversationContextEnhancer(conversation_store=conversation_store)
    
    # Create handler with mocks
    handler = EnhancedChatHandler(
        agent=mock_agent,
        learning_manager=mock_learning_manager,
        csv_manager=csv_manager,
        sql_runner=mock_sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer
    )
    
    # Mock the _find_latest_csv method to simulate CSV creation
    original_find_latest_csv = handler._find_latest_csv
    
    csv_counter = 0
    def mock_find_latest_csv():
        nonlocal csv_counter
        # First call returns None (before query)
        # Second call returns a CSV path (after query)
        if csv_counter == 0:
            csv_counter += 1
            return None
        else:
            # Create a dummy CSV file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
            mock_df.to_csv(temp_file.name, index=False)
            return temp_file.name
    
    handler._find_latest_csv = mock_find_latest_csv
    
    # Test the handler
    request = {
        "message": "Show me all tables",
        "headers": {
            "x-user-id": "test_user",
            "x-username": "tester",
            "x-user-groups": "api_users"
        }
    }
    
    try:
        response = await handler.handle_chat_request(request)
        
        print(f"\nResponse from handler:")
        print(f"  Answer length: {len(response.get('answer', ''))}")
        print(f"  SQL: '{response.get('sql', '')}'")
        print(f"  SQL length: {len(response.get('sql', ''))}")
        print(f"  CSV URL: {response.get('csv_url', 'None')}")
        print(f"  Success: {response.get('success', False)}")
        print(f"  Tool used: {response.get('tool_used', False)}")
        
        # Check if SQL was captured
        sql = response.get('sql', '')
        if sql and sql.strip():
            print(f"\n✓ SUCCESS: SQL was captured from tool call!")
            print(f"   SQL: {sql}")
            return True
        else:
            print(f"\n✗ FAILURE: SQL was not captured")
            print(f"   This suggests tool_call_component is not being processed correctly")
            return False
            
    except Exception as e:
        print(f"\nError in handler: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_handler_without_tool_call_components():
    """Test handler when agent doesn't yield tool call components (simulating real Vanna behavior)"""
    
    print("\n" + "="*60)
    print("Testing handler when agent doesn't yield tool call components")
    print("="*60)
    
    # Create mock agent that doesn't yield tool_call_component
    # This simulates what we observed in our inspection
    class MockComponent:
        def __init__(self, text=None):
            self.simple_component = MagicMock() if text else None
            if text and self.simple_component:
                self.simple_component.text = text
            self.tool_call_component = None  # No tool call component!
            self.tool_result_component = None
    
    mock_agent = MagicMock()
    
    # Simulate agent response without tool call components
    # This is what we observed in inspect_components.py
    async def mock_send_message(*args, **kwargs):
        # Yield components without tool_call_component
        yield MockComponent(text="To display all tables in the database, I can execute a query to list them. Let me run that for you.")
        yield MockComponent(text="Executing query: SELECT table_name FROM information_schema.tables WHERE table_schema = 'mapa_db'")
        yield MockComponent(text="Results saved to file: query_results_abc123.csv")
        yield MockComponent(text="Here are the tables in the mapa_db database:\n- aankoop\n- another_table\n- test_table")
    
    mock_agent.send_message = mock_send_message
    
    # Create other mocks
    mock_learning_manager = MagicMock()
    mock_learning_manager.enhance_question_with_learned_patterns.return_value = "Show me all tables"
    
    mock_sql_runner = MagicMock()
    mock_df = pd.DataFrame({
        'TABLE_SCHEMA': ['mapa_db', 'mapa_db'],
        'TABLE_NAME': ['aankoop', 'another_table']
    })
    mock_sql_runner.run_sql.return_value = mock_df
    
    csv_manager = CSVResultManager()
    conversation_store = ConversationStore()
    conversation_enhancer = ConversationContextEnhancer(conversation_store=conversation_store)
    
    # Create handler
    handler = EnhancedChatHandler(
        agent=mock_agent,
        learning_manager=mock_learning_manager,
        csv_manager=csv_manager,
        sql_runner=mock_sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer
    )
    
    # Mock CSV detection
    csv_counter = 0
    original_find_latest_csv = handler._find_latest_csv
    
    def mock_find_latest_csv():
        nonlocal csv_counter
        if csv_counter == 0:
            csv_counter += 1
            return None
        else:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
            mock_df.to_csv(temp_file.name, index=False)
            return temp_file.name
    
    handler._find_latest_csv = mock_find_latest_csv
    
    # Test
    request = {
        "message": "Show me all tables",
        "headers": {
            "x-user-id": "test_user",
            "x-username": "tester", 
            "x-user-groups": "api_users"
        }
    }
    
    try:
        response = await handler.handle_chat_request(request)
        
        print(f"\nResponse from handler (no tool call components):")
        print(f"  Answer length: {len(response.get('answer', ''))}")
        print(f"  SQL: '{response.get('sql', '')}'")
        print(f"  SQL length: {len(response.get('sql', ''))}")
        
        sql = response.get('sql', '')
        if sql and sql.strip():
            print(f"\n✓ SUCCESS: SQL was extracted from response text!")
            print(f"   SQL: {sql[:200]}...")
            return True
        else:
            print(f"\n✗ FAILURE: SQL was not extracted from response text")
            print(f"   Answer preview: {response.get('answer', '')[:500]}")
            return False
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 60)
    print("Testing EnhancedChatHandler SQL Capture")
    print("=" * 60)
    
    # Test 1: With tool call components (ideal case)
    print("\nTest 1: Agent yields tool call components")
    test1_passed = await test_handler_with_mock_agent()
    
    # Test 2: Without tool call components (real Vanna behavior)
    test2_passed = await test_handler_without_tool_call_components()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Test 1 (with tool call components): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Test 2 (without tool call components): {'PASSED' if test2_passed else 'FAILED'}")
    print("=" * 60)
    
    if test2_passed:
        print("\n✓ The fix should work for real Vanna agent behavior!")
    else:
        print("\n✗ The fix might not work for real Vanna agent behavior.")
        print("  Need to improve SQL extraction from response text.")

if __name__ == "__main__":
    asyncio.run(main())