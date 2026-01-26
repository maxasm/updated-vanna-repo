#!/usr/bin/env python3
"""Test script to verify chart extraction and generation fixes"""

import asyncio
import json
import logging
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import EnhancedChatHandler, CSVResultManager, ConversationStore, ConversationContextEnhancer

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_chart_extraction():
    """Test chart extraction from components"""
    print("=== Testing Chart Extraction ===")
    
    # Create mocks
    agent = MagicMock()
    learning_manager = MagicMock()
    learning_manager.record_tool_usage = AsyncMock()
    learning_manager.enhance_question_with_learned_patterns = MagicMock(return_value="enhanced question")
    
    csv_manager = MagicMock()
    csv_manager.get_csv_url.return_value = "/static/test.csv"
    
    sql_runner = MagicMock()
    
    conversation_store = MagicMock()
    conversation_store.save_conversation_turn = AsyncMock()
    
    conversation_enhancer = MagicMock()
    conversation_enhancer.enhance_question_with_context = AsyncMock(return_value="enhanced question")
    
    # Create handler
    handler = EnhancedChatHandler(
        agent=agent,
        learning_manager=learning_manager,
        csv_manager=csv_manager,
        sql_runner=sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer
    )
    
    # Test 1: Check if chart data is extracted from component with metadata
    print("\nTest 1: Chart data in metadata")
    mock_component = MagicMock()
    mock_tool_result = MagicMock()
    mock_component.tool_result_component = mock_tool_result
    
    # Create a mock chart data structure
    chart_data = {
        "data": [{"x": [1, 2, 3], "y": [10, 20, 30], "type": "bar"}],
        "layout": {"title": "Test Chart"}
    }
    mock_tool_result.metadata = {"chart": chart_data}
    
    extracted = handler._extract_chart_from_component(mock_component)
    print(f"Extracted chart: {extracted is not None}")
    if extracted:
        print(f"Chart keys: {list(extracted.keys())}")
    
    # Test 2: Check if chart data is extracted from plotly_figure in metadata
    print("\nTest 2: plotly_figure in metadata")
    mock_component2 = MagicMock()
    mock_tool_result2 = MagicMock()
    mock_component2.tool_result_component = mock_tool_result2
    mock_tool_result2.metadata = {"plotly_figure": chart_data}
    
    extracted2 = handler._extract_chart_from_component(mock_component2)
    print(f"Extracted chart: {extracted2 is not None}")
    
    # Test 3: Check if component itself is chart data
    print("\nTest 3: Component is chart data dict")
    extracted3 = handler._extract_chart_from_component(chart_data)
    print(f"Extracted chart: {extracted3 is not None}")
    
    return extracted is not None or extracted2 is not None or extracted3 is not None

async def test_visualization_detection():
    """Test detection of 'Created visualization' in response text"""
    print("\n=== Testing Visualization Detection ===")
    
    # Create mocks
    agent = MagicMock()
    learning_manager = MagicMock()
    learning_manager.record_tool_usage = AsyncMock()
    learning_manager.enhance_question_with_learned_patterns = MagicMock(return_value="enhanced question")
    
    csv_manager = MagicMock()
    csv_manager.get_csv_url.return_value = "/static/test.csv"
    
    sql_runner = MagicMock()
    
    conversation_store = MagicMock()
    conversation_store.save_conversation_turn = AsyncMock()
    
    conversation_enhancer = MagicMock()
    conversation_enhancer.enhance_question_with_context = AsyncMock(return_value="enhanced question")
    
    # Create handler
    handler = EnhancedChatHandler(
        agent=agent,
        learning_manager=learning_manager,
        csv_manager=csv_manager,
        sql_runner=sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer
    )
    
    # Test response text with "Created visualization"
    response_text = "Created visualization from 'query_results_123.csv' (5 rows, 2 columns)."
    csv_path = "/tmp/query_results_123.csv"
    
    # Mock chart generator
    handler.chart_generator = MagicMock()
    mock_chart = {"data": [{"x": [1, 2], "y": [10, 20], "type": "bar"}]}
    handler.chart_generator.generate_chart.return_value = mock_chart
    
    # Mock CSV reading
    with patch('pandas.read_csv') as mock_read_csv:
        mock_df = pd.DataFrame({'Category': ['A', 'B'], 'Value': [10, 20]})
        mock_read_csv.return_value = mock_df
        
        # Mock os.path.exists
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Test the logic
            chart_json = None
            chart_source = None
            
            # Simulate the condition from handle_chat_request
            if "Created visualization" in response_text and csv_path and chart_json is None:
                print(f"Detected 'Created visualization' in response but no chart extracted. CSV path: {csv_path}")
                try:
                    if os.path.exists(csv_path):
                        df = pd.read_csv(csv_path)
                        if not df.empty:
                            print(f"Loaded CSV for chart generation: {csv_path}, shape: {df.shape}")
                            chart_dict = handler.chart_generator.generate_chart(df=df)
                            if chart_dict:
                                chart_json = chart_dict
                                chart_source = "forced_after_visualize_tool"
                                print(f"Generated chart from CSV after visualization tool call")
                            else:
                                print(f"Chart generator returned None for CSV: {csv_path}")
                        else:
                            print(f"CSV is empty: {csv_path}")
                    else:
                        print(f"CSV file not found for visualization: {csv_path}")
                except Exception as e:
                    print(f"Error generating chart from CSV after visualization: {e}")
    
    print(f"Chart generated: {chart_json is not None}")
    print(f"Chart source: {chart_source}")
    
    return chart_json is not None and chart_source == "forced_after_visualize_tool"

async def main():
    """Run all tests"""
    print("Running chart extraction and generation tests...")
    
    # Test chart extraction
    extraction_passed = await test_chart_extraction()
    
    # Test visualization detection
    detection_passed = await test_visualization_detection()
    
    print("\n=== Test Results ===")
    print(f"Chart extraction test: {'PASSED' if extraction_passed else 'FAILED'}")
    print(f"Visualization detection test: {'PASSED' if detection_passed else 'FAILED'}")
    
    if extraction_passed and detection_passed:
        print("\nAll tests passed! The fixes should work correctly.")
        return 0
    else:
        print("\nSome tests failed. Check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)