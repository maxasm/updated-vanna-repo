import asyncio
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Test the SQL extraction regex from api.py
def _extract_sql_from_response(response_text: str) -> str:
    """Extract SQL query from agent response text"""
    # Try to find SQL in code blocks
    sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
    if not sql_match:
        # Try other SQL patterns
        sql_match = re.search(r'SELECT .*?FROM', response_text, re.DOTALL | re.IGNORECASE)
    
    if sql_match:
        # Check if we have a capture group (from the first pattern)
        if sql_match.lastindex and sql_match.lastindex >= 1:
            sql_query = sql_match.group(1)
        else:
            sql_query = sql_match.group(0)
        return sql_query.strip()
    
    return ""

# Test cases
test_cases = [
    # Case 1: SQL in code block
    ("Here's the query:\n```sql\nSELECT * FROM information_schema.tables\n```\nResults saved to file.",
     "SELECT * FROM information_schema.tables"),
    
    # Case 2: SQL without code block
    ("I'll run SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
     "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"),
    
    # Case 3: No SQL
    ("Here are your results: table1, table2, table3", ""),
    
    # Case 4: SHOW TABLES command (won't match SELECT ... FROM pattern)
    ("Executing: SHOW TABLES", ""),
    
    # Case 5: Complex SQL with multiple lines
    ("""I'll run this query:
SELECT 
    table_schema,
    table_name
FROM 
    information_schema.tables
WHERE 
    table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY 
    table_schema, table_name""",
     """SELECT 
    table_schema,
    table_name
FROM 
    information_schema.tables
WHERE 
    table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY 
    table_schema, table_name"""),
]

print("Testing SQL extraction regex:")
for i, (input_text, expected) in enumerate(test_cases):
    result = _extract_sql_from_response(input_text)
    match = "✓" if result == expected else "✗"
    print(f"\nTest {i+1} {match}:")
    print(f"  Input: {input_text[:80]}...")
    print(f"  Expected: {expected[:80]}..." if expected else "  Expected: (empty)")
    print(f"  Got: {result[:80]}..." if result else "  Got: (empty)")

# Now let's check what actual responses look like by running a real query
print("\n\nNow let's test with a real API call...")
import requests
import json
import time

def test_real_api():
    # Start API if not running
    try:
        response = requests.get("http://localhost:8001/api/v1/health", timeout=2)
        print("API is already running")
    except:
        print("API is not running. Starting it...")
        import subprocess
        import sys
        api_process = subprocess.Popen(
            [sys.executable, "api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": "."}
        )
        time.sleep(5)
    
    # Send a test query
    url = "http://localhost:8001/api/v1/chat"
    payload = {
        "message": "Show me all tables in the database",
        "headers": {
            "x-user-id": "test_user",
            "x-username": "tester",
            "x-user-groups": "api_users"
        }
    }
    
    try:
        print("Sending request to API...")
        response = requests.post(url, json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse data:")
            print(f"  Answer length: {len(data.get('answer', ''))} chars")
            print(f"  SQL: {data.get('sql', 'None')}")
            print(f"  CSV URL: {data.get('csv_url', 'None')}")
            print(f"  Success: {data.get('success', False)}")
            
            # Check the answer text for SQL patterns
            answer = data.get('answer', '')
            print(f"\nFirst 500 chars of answer:")
            print(answer[:500])
            
            # Try to extract SQL from answer
            extracted = _extract_sql_from_response(answer)
            print(f"\nExtracted SQL from answer: {extracted}")
            
            # Also check for SHOW TABLES or other patterns
            show_tables_match = re.search(r'SHOW\s+TABLES', answer, re.IGNORECASE)
            if show_tables_match:
                print(f"Found SHOW TABLES in answer")
            
            # Check for information_schema patterns
            info_schema_match = re.search(r'information_schema\.tables', answer, re.IGNORECASE)
            if info_schema_match:
                print(f"Found information_schema.tables in answer")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"API request failed: {e}")

if __name__ == "__main__":
    test_real_api()