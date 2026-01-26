import os
import mysql.connector
from dotenv import load_dotenv

# Load your .env file
load_dotenv()

def test_connection():
    print("--- Database Connection Test ---")
    
    # Get variables from .env
    config = {
        'host': os.getenv("MYSQL_DO_HOST", "127.0.0.1"),
        'port': int(os.getenv("MYSQL_DO_PORT", 3306)),
        'user': os.getenv("MYSQL_DO_USER"),
        'password': os.getenv("MYSQL_DO_PASSWORD"),
        'database': os.getenv("MYSQL_DO_DATABASE")
    }

    print(f"Attempting to connect to {config['host']}:{config['port']}...")
    print(f"User: {config['user']}, Database: {config['database']}")

    try:
        # Establish connection
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            print("\n✅ SUCCESS: Connected to MySQL successfully!")
            
            # Test a simple query to see if data.sql loaded
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            
            print(f"Tables found in database: {len(tables)}")
            for (table_name,) in tables:
                print(f" - {table_name}")
                
            cursor.close()
            conn.close()
            
    except mysql.connector.Error as err:
        print(f"\n❌ ERROR: {err}")
        if err.errno == 2003:
            print("Tip: Ensure your Docker container is running and port 3306 is mapped.")
        elif err.errno == 1045:
            print("Tip: Check your Username or Password.")
        elif err.errno == 1049:
            print("Tip: The database name in .env doesn't exist yet.")

if __name__ == "__main__":
    test_connection()