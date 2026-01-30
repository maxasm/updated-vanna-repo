#!/usr/bin/env python3
"""
Test database connection using credentials from .env file
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database configuration
DB_HOST = os.getenv("MYSQL_DO_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("MYSQL_DO_PORT", "3306"))
DB_USER = os.getenv("MYSQL_DO_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_DO_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DO_DATABASE", "classicmodels")

print("=" * 60)
print("DATABASE CONNECTION TEST")
print("=" * 60)
print(f"\nConfiguration:")
print(f"  Host:     {DB_HOST}")
print(f"  Port:     {DB_PORT}")
print(f"  User:     {DB_USER}")
print(f"  Database: {DB_NAME}")
print(f"  Password: {'*' * len(DB_PASSWORD) if DB_PASSWORD else '(empty)'}")
print()

# Test connection
try:
    import mysql.connector
    
    print("Attempting to connect to MySQL...")
    
    # Connect to MySQL
    connection = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connect_timeout=10
    )
    
    if connection.is_connected():
        print("✅ Connection successful!")
        
        # Get server info
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"\n📊 MySQL Server Version: {version[0]}")
        
        # Get database info
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"📁 Current Database: {current_db[0]}")
        
        # List tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\n📋 Tables in '{DB_NAME}' ({len(tables)} total):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]}: {count} rows")
        
        # Close cursor and connection
        cursor.close()
        connection.close()
        print("\n✅ Connection test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Failed to connect to database")
        sys.exit(1)
        
except ImportError:
    print("❌ Error: mysql-connector-python is not installed")
    print("\nTo install, run:")
    print("  pip install mysql-connector-python")
    sys.exit(1)
    
except mysql.connector.Error as e:
    print(f"❌ MySQL Error: {e}")
    print(f"\nError Code: {e.errno}")
    print(f"SQL State: {e.sqlstate}")
    print(f"Message: {e.msg}")
    
    # Provide helpful suggestions
    if e.errno == 2003:
        print("\n💡 Suggestion: Cannot connect to MySQL server.")
        print("   - Check if MySQL is running")
        print("   - Verify the host and port are correct")
    elif e.errno == 1045:
        print("\n💡 Suggestion: Access denied.")
        print("   - Check username and password in .env file")
    elif e.errno == 1049:
        print("\n💡 Suggestion: Unknown database.")
        print(f"   - Database '{DB_NAME}' does not exist")
        print("   - Create the database or check the DB_NAME in .env")
    
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
