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
        sql_query = sql_match.group(1) if sql_match.group(1) else sql_match.group(0)
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
    
    # Case 4: SHOW TABLES command
    ("Executing: SHOW TABLES", "SHOW TABLES"),
    
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

# Now let's check what actual responses look like
print("\n\nChecking actual CSV files for SQL patterns...")
import glob
import pandas as pd

# Look for recent CSV files
csv_files = glob.glob("**/*.csv", recursive=True)
csv_files.sort(key=os.path.getmtime, reverse=True)

recent_files = csv_files[:3]
for csv_file in recent_files:
    print(f"\nChecking {csv_file}:")
    try:
        df = pd.read_csv(csv_file)
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        # Check if this looks like a SHOW TABLES or information_schema query result
        if 'TABLE_NAME' in df.columns or 'table_name' in df.columns:
            print(f"  Looks like a tables list query")
        elif len(df.columns) == 1 and df.columns[0].lower() in ['tables_in_', 'table']:
            print(f"  Looks like a SHOW TABLES result")
    except Exception as e:
        print(f"  Error reading CSV: {e}")