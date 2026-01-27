import asyncio
import sys
import os
import json
from pathlib import Path

# Add current directory to path to import from api.py
sys.path.insert(0, str(Path(__file__).parent))

from api import EnhancedChatHandler, CSVResultManager, ConversationStore, ConversationContextEnhancer
from learning_manager import LearningManager
from vanna.integrations.mysql import MySQLRunner
from dotenv import load_dotenv

load_dotenv()

async def test_sql_extraction():
    print("Testing SQL extraction fix...")
    
    # Create mock objects for testing
    class MockAgent:
        pass
    
    class MockLearningManager:
        def enhance_question_with_learned_patterns(self, question):
            return question
    
    class MockSQLRunner:
        def run_sql(self, sql):
            import pandas as pd
            # Return a mock dataframe
            return pd.DataFrame({"test": [1, 2, 3]})
    
    # Initialize components
    agent = MockAgent()
    learning_manager = MockLearningManager()
    csv_manager = CSVResultManager()
    sql_runner = MockSQLRunner()
    conversation_store = ConversationStore()
    conversation_enhancer = ConversationContextEnhancer(conversation_store=conversation_store)
    
    # Create handler
    handler = EnhancedChatHandler(
        agent=agent,
        learning_manager=learning_manager,
        csv_manager=csv_manager,
        sql_runner=sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer
    )
    
    # Test cases for SQL extraction
    test_cases = [
        {
            "name": "SQL in code block",
            "response": "Here's the query:\n```sql\nSELECT * FROM information_schema.tables\n```\nResults saved to file.",
            "expected": "SELECT * FROM information_schema.tables"
        },
        {
            "name": "SHOW TABLES command",
            "response": "Executing: SHOW TABLES; then I'll process results",
            "expected": "SHOW TABLES"
        },
        {
            "name": "SELECT without code block",
            "response": "I'll run SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
            "expected": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        },
        {
            "name": "Complex multi-line SQL",
            "response": """I'll run this query:
SELECT 
    table_schema,
    table_name
FROM 
    information_schema.tables
WHERE 
    table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY 
    table_schema, table_name;
Then I'll format the results.""",
            "expected": """SELECT 
    table_schema,
    table_name
FROM 
    information_schema.tables
WHERE 
    table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY 
    table_schema, table_name"""
        },
        {
            "name": "No SQL",
            "response": "Here are your results: table1, table2, table3",
            "expected": ""
        }
    ]
    
    print("\nTesting SQL extraction method:")
    all_passed = True
    for test in test_cases:
        result = handler._extract_sql_from_response(test["response"])
        passed = result == test["expected"]
        all_passed = all_passed and passed
        
        status = "✓" if passed else "✗"
        print(f"\n{status} {test['name']}:")
        print(f"  Expected: {test['expected'][:80]}..." if test['expected'] else "  Expected: (empty)")
        print(f"  Got: {result[:80]}..." if result else "  Got: (empty)")
        if not passed:
            print(f"  Mismatch!")
    
    # Test the CSV finding method
    print("\n\nTesting CSV file detection:")
    csv_path = handler._find_latest_csv()
    if csv_path:
        print(f"Found CSV file: {csv_path}")
    else:
        print("No CSV files found (this is OK for testing)")
    
    return all_passed

async def test_real_api():
    print("\n\nTesting with real API...")
    
    # Start the API server
    import subprocess
    import time
    import requests
    
    print("Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": "."}
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(8)
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8001/api/v1/health", timeout=5)
        print(f"Health check: {response.status_code}")
        
        if response.status_code == 200:
            # Test chat endpoint
            print("\nTesting chat endpoint with 'Show me all tables'...")
            payload = {
                "message": "Show me all tables in the database",
                "headers": {
                    "x-user-id": "test_user",
                    "x-username": "tester",
                    "x-user-groups": "api_users"
                }
            }
            
            response = requests.post("http://localhost:8001/api/v1/chat", json=payload, timeout=30)
            print(f"Chat response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nResponse data:")
                print(f"  Answer length: {len(data.get('answer', ''))} chars")
                print(f"  SQL: {data.get('sql', 'None')}")
                print(f"  CSV URL: {data.get('csv_url', 'None')}")
                print(f"  Success: {data.get('success', False)}")
                
                # Check if SQL was captured
                sql = data.get('sql', '')
                if sql:
                    print(f"\n✓ SUCCESS: SQL was captured: {sql[:100]}...")
                    return True
                else:
                    print(f"\n✗ FAILURE: SQL was not captured (empty string)")
                    # Print first 500 chars of answer to see what we got
                    answer = data.get('answer', '')
                    print(f"\nFirst 500 chars of answer:")
                    print(answer[:500])
                    return False
            else:
                print(f"Chat request failed: {response.text}")
                return False
        else:
            print(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error testing API: {e}")
        return False
    finally:
        # Kill the API server
        print("\nStopping API server...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()

async def main():
    print("=" * 60)
    print("Testing SQL extraction fix for Vanna AI API")
    print("=" * 60)
    
    # Test 1: SQL extraction method
    extraction_passed = await test_sql_extraction()
    
    # Test 2: Real API test (optional - might fail if MySQL not available)
    print("\n" + "=" * 60)
    print("Note: Real API test requires MySQL connection.")
    print("Skipping real API test for now to avoid dependency issues.")
    print("=" * 60)
    
    # Instead, let's test with a mock that simulates the actual issue
    print("\n\nTesting simulated agent response...")
    
    # Simulate what the agent might return for "Show me all tables"
    simulated_response = """To display all tables in the database, I can execute a query to list them. Let me run that for you.

Executing query: SELECT table_name FROM information_schema.tables WHERE table_schema = 'mapa_db'

Results saved to file: query_results_abc123.csv

Here are the tables in the mapa_db database:
- aankoop
- another_table
- test_table

You can download the full results from the CSV file."""
    
    from api import EnhancedChatHandler
    handler = EnhancedChatHandler(None, None, None, None, None, None)
    
    extracted_sql = handler._extract_sql_from_response(simulated_response)
    print(f"Extracted SQL from simulated response: {extracted_sql}")
    
    if extracted_sql:
        print("✓ SQL extraction works on simulated agent response")
    else:
        print("✗ SQL extraction failed on simulated agent response")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"SQL extraction tests: {'PASSED' if extraction_passed else 'FAILED'}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())