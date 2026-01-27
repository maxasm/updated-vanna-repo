import re

# Copy the exact extraction function from api.py
def _extract_sql_from_response(response_text: str) -> str:
    """Improved SQL extraction from agent response text"""
    # First, try to find SQL in code blocks (most reliable)
    # Match ```sql ... ``` or ```SQL ... ```
    sql_match = re.search(r'```(?:sql|SQL)\s*(.*?)\s*```', response_text, re.DOTALL)
    if sql_match:
        sql_query = sql_match.group(1).strip()
        print(f"Extracted SQL from code block: {sql_query[:100]}...")
        return sql_query
    
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
            print(f"Extracted SQL using pattern '{pattern[:30]}...': {sql[:100]}...")
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
                    print(f"Extracted SQL starting with '{keyword}': {sql[:100]}...")
                    return sql
    
    print("No SQL found in response text")
    return ""

# Test with the actual response from the curl command
response_text = """I can’t connect to the database because the client needs the “cryptography” package to authenticate (MySQL’s sha256_password/caching_sha2_password). Once that’s installed or the auth method is adjusted, I’ll list the tables.

Options to fix:
- Install the required package (recommended):
  - pip install cryptography
- Or use a MySQL user with a compatible plugin:
  - ALTER USER 'your_user'@'your_host' IDENTIFIED WITH mysql_native_password BY 'your_password'; FLUSH PRIVILEGES;
- Or provide alternative connection details that don’t require sha256/caching_sha2.

Query I will run once the connection works:
SELECT table_name AS `Table`
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY table_name;

Would you like me to try again after you install cryptography or provide an alternate user/connection?

Summary: Attempted to query tables, but authentication failed due to missing “cryptography” for MySQL’s sha256/caching_sha2; provided fixes and the exact query I’ll run once resolved."""

print("Testing SQL extraction on actual response...")
print("=" * 80)
result = _extract_sql_from_response(response_text)
print(f"\nResult: '{result}'")
print(f"Result length: {len(result)}")

# Also test a simpler version
print("\n" + "=" * 80)
print("Testing with just the SQL part...")
simple_test = """Query I will run once the connection works:
SELECT table_name AS `Table`
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY table_name;"""

result2 = _extract_sql_from_response(simple_test)
print(f"Result: '{result2}'")

# Let me also test the regex pattern directly
print("\n" + "=" * 80)
print("Testing regex pattern directly...")
pattern = r'(SELECT\s+(?:.|\n)*?(?:FROM\s+(?:.|\n)*?)(?:\s+WHERE\s+(?:.|\n)*?)?(?:\s+GROUP BY\s+(?:.|\n)*?)?(?:\s+ORDER BY\s+(?:.|\n)*?)?(?:\s+LIMIT\s+\d+)?)(?:\s*;|$)'
match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
if match:
    print(f"Pattern matched!")
    print(f"Matched text: {match.group(1)[:200]}...")
else:
    print("Pattern did not match")
    
    # Try a simpler pattern
    print("\nTrying simpler pattern...")
    simple_pattern = r'(SELECT.*?;)'
    match2 = re.search(simple_pattern, response_text, re.IGNORECASE | re.DOTALL)
    if match2:
        print(f"Simple pattern matched: {match2.group(1)[:200]}...")
    else:
        print("Simple pattern also didn't match")
        
        # Try even simpler
        print("\nTrying to find SELECT...FROM pattern...")
        select_from_pattern = r'SELECT.*?FROM.*?WHERE.*?ORDER BY.*?;'
        match3 = re.search(select_from_pattern, response_text, re.IGNORECASE | re.DOTALL)
        if match3:
            print(f"SELECT...FROM pattern matched: {match3.group()[:200]}...")
        else:
            print("SELECT...FROM pattern didn't match")
            
            # Just find SELECT to end of line
            print("\nTrying to find SELECT to end of line...")
            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                if 'SELECT' in line.upper():
                    print(f"Found SELECT at line {i}: {line}")
                    # Check next few lines
                    for j in range(i, min(i+5, len(lines))):
                        print(f"  Line {j}: {lines[j]}")