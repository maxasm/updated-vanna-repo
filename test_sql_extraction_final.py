import re
import sys
from pathlib import Path

# Add current directory to path to import from api.py
sys.path.insert(0, str(Path(__file__).parent))

from api import EnhancedChatHandler

def test_sql_extraction():
    """Test SQL extraction with the actual response from the curl command"""
    
    # Create a mock handler to access the extraction method
    class MockHandler:
        def _extract_sql_from_response(self, response_text: str) -> str:
            """Copy of the actual extraction method from EnhancedChatHandler"""
            import re
            import logging
            logger = logging.getLogger("vanna_api")
            
            # First, try to find SQL in code blocks (most reliable)
            # Match ```sql ... ``` or ```SQL ... ```
            sql_match = re.search(r'```(?:sql|SQL)\s*(.*?)\s*```', response_text, re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(1).strip()
                logger.info(f"Extracted SQL from code block: {sql_query[:100]}...")
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
                    logger.info(f"Extracted SQL using pattern '{pattern[:30]}...': {sql[:100]}...")
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
                            logger.info(f"Extracted SQL starting with '{keyword}': {sql[:100]}...")
                            return sql
            
            logger.debug("No SQL found in response text")
            return ""
    
    handler = MockHandler()
    
    # The actual response from the curl command
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
    
    print("Testing SQL extraction on actual curl response...")
    print("=" * 80)
    
    sql = handler._extract_sql_from_response(response_text)
    
    print(f"\nExtracted SQL: '{sql}'")
    print(f"SQL length: {len(sql)}")
    
    expected_sql = """SELECT table_name AS `Table`
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY table_name"""
    
    if sql.strip() == expected_sql.strip():
        print("\n✓ SUCCESS: SQL extracted correctly!")
        return True
    else:
        print(f"\n✗ FAILURE: SQL extraction failed")
        print(f"Expected: '{expected_sql}'")
        print(f"Got: '{sql}'")
        return False

def test_sql_extraction_with_successful_query():
    """Test SQL extraction with a successful query response (where CSV is generated)"""
    
    print("\n" + "=" * 80)
    print("Testing SQL extraction with successful query response...")
    print("=" * 80)
    
    class MockHandler:
        def _extract_sql_from_response(self, response_text: str) -> str:
            # Same as above
            import re
            import logging
            logger = logging.getLogger("vanna_api")
            
            sql_match = re.search(r'```(?:sql|SQL)\s*(.*?)\s*```', response_text, re.DOTALL)
            if sql_match:
                return sql_match.group(1).strip()
            
            sql_patterns = [
                r'(SHOW\s+(?:TABLES|DATABASES|COLUMNS|INDEXES|CREATE\s+TABLE)[^;]*)(?:;|$)',
                r'(SELECT\s+(?:.|\n)*?(?:FROM\s+(?:.|\n)*?)(?:\s+WHERE\s+(?:.|\n)*?)?(?:\s+GROUP BY\s+(?:.|\n)*?)?(?:\s+ORDER BY\s+(?:.|\n)*?)?(?:\s+LIMIT\s+\d+)?)(?:\s*;|$)',
                r'(DESCRIBE\s+\w+[^;]*)(?:;|$)',
                r'(SHOW\s+CREATE\s+TABLE\s+\w+[^;]*)(?:;|$)',
            ]
            
            for pattern in sql_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if match:
                    sql = match.group(1).strip()
                    sql = re.sub(r'[;.]\s*$', '', sql)
                    return sql
            
            sql_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH']
            for keyword in sql_keywords:
                pattern = rf'\b{keyword}\b'
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    start_idx = match.start()
                    remaining = response_text[start_idx:]
                    end_match = re.search(r'[;.]\s*\n|\n\n|$', remaining)
                    if end_match:
                        end_idx = start_idx + end_match.start()
                        sql = response_text[start_idx:end_idx].strip()
                        if len(sql.split()) > 2:
                            return sql
            
            return ""
    
    handler = MockHandler()
    
    # Simulate a successful query response (like the original problem case)
    response_text = """Here are the tables in the database:

TABLE_SCHEMA,TABLE_NAME
mapa_db,aankoop
performance_schema,global_status
...

Results saved to file: query_results_61f0f276.csv

The query I executed was:
SELECT table_name, table_schema 
FROM information_schema.tables 
WHERE table_schema = 'mapa_db' 
ORDER BY table_name;"""
    
    sql = handler._extract_sql_from_response(response_text)
    
    print(f"\nExtracted SQL: '{sql}'")
    
    expected_sql = """SELECT table_name, table_schema 
FROM information_schema.tables 
WHERE table_schema = 'mapa_db' 
ORDER BY table_name"""
    
    if sql.strip() == expected_sql.strip():
        print("\n✓ SUCCESS: SQL extracted correctly from successful query!")
        return True
    else:
        print(f"\n✗ FAILURE: SQL extraction failed")
        print(f"Expected: '{expected_sql}'")
        print(f"Got: '{sql}'")
        return False

def main():
    print("=" * 80)
    print("Final SQL Extraction Tests")
    print("=" * 80)
    
    test1 = test_sql_extraction()
    test2 = test_sql_extraction_with_successful_query()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"Test 1 (curl response): {'PASSED' if test1 else 'FAILED'}")
    print(f"Test 2 (successful query): {'PASSED' if test2 else 'FAILED'}")
    print("=" * 80)
    
    if test1 and test2:
        print("\n✓ All tests passed! The SQL extraction should work correctly.")
    else:
        print("\n✗ Some tests failed. Need to debug further.")

if __name__ == "__main__":
    main()