import re

def extract_sql_from_response_final(response_text: str) -> str:
    """Final improved SQL extraction from agent response text"""
    # First, try to find SQL in code blocks (most reliable)
    # Match ```sql ... ``` or ```SQL ... ```
    sql_match = re.search(r'```(?:sql|SQL)\s*(.*?)\s*```', response_text, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Try to find SQL statements without code blocks
    # Look for common SQL patterns - improved to stop at semicolon or end of line
    sql_patterns = [
        # SHOW commands - stop at semicolon or end
        r'(SHOW\s+(?:TABLES|DATABASES|COLUMNS|INDEXES|CREATE\s+TABLE)[^;]*)(?:;|$)',
        # SELECT statements (more complete capture)
        r'(SELECT\s+(?:.|\n)*?(?:FROM\s+(?:.|\n)*?)(?:\s+WHERE\s+(?:.|\n)*?)?(?:\s+GROUP BY\s+(?:.|\n)*?)?(?:\s+ORDER BY\s+(?:.|\n)*?)?(?:\s+LIMIT\s+\d+)?)(?:\s*;|$)',
        # DESCRIBE commands
        r'(DESCRIBE\s+\w+[^;]*)(?:;|$)',
        # MySQL specific: SHOW CREATE TABLE
        r'(SHOW\s+CREATE\s+TABLE\s+\w+[^;]*)(?:;|$)',
    ]
    
    for pattern in sql_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1).strip()
            # Clean up: remove trailing punctuation and extra whitespace
            sql = re.sub(r'[;.]\s*$', '', sql)
            return sql
    
    # Try to find any SQL-like statement that starts with common keywords
    sql_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH']
    for keyword in sql_keywords:
        # Find the keyword in text (case insensitive)
        pattern = rf'\b{keyword}\b'
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            start_idx = match.start()
            # Look for end of statement (semicolon, double newline, or end of text)
            remaining = response_text[start_idx:]
            # Try to find a reasonable end point
            end_match = re.search(r'[;.]\s*\n|\n\n|$', remaining)
            if end_match:
                end_idx = start_idx + end_match.start()
                sql = response_text[start_idx:end_idx].strip()
                # Basic validation: should contain SQL keywords
                if len(sql.split()) > 2:  # At least 3 words (e.g., "SHOW TABLES")
                    return sql
    
    return ""

# Test the final extraction
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
    ("Executing: SHOW TABLES; then I'll process results", "SHOW TABLES"),
    
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
    table_schema, table_name;
Then I'll format the results.""",
     """SELECT 
    table_schema,
    table_name
FROM 
    information_schema.tables
WHERE 
    table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY 
    table_schema, table_name"""),
    
    # Case 6: SHOW CREATE TABLE
    ("Let me show the structure: SHOW CREATE TABLE users;", "SHOW CREATE TABLE users"),
    
    # Case 7: SQL with semicolon in the middle of text
    ("Query: SELECT id, name FROM products WHERE price > 100; This returns expensive products.",
     "SELECT id, name FROM products WHERE price > 100"),
    
    # Case 8: SHOW TABLES without semicolon
    ("I'll execute SHOW TABLES now", "SHOW TABLES"),
]

print("Testing final SQL extraction:")
for i, (input_text, expected) in enumerate(test_cases):
    result = extract_sql_from_response_final(input_text)
    match = "✓" if result == expected else "✗"
    print(f"\nTest {i+1} {match}:")
    print(f"  Input: {input_text[:80]}...")
    print(f"  Expected: {expected[:80]}..." if expected else "  Expected: (empty)")
    print(f"  Got: {result[:80]}..." if result else "  Got: (empty)")
    if result != expected:
        print(f"  Difference: expected '{expected}', got '{result}'")