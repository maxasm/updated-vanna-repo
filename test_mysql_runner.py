import os
import asyncio
from dotenv import load_dotenv
from vanna.integrations.mysql import MySQLRunner
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.core.tool.models import ToolContext
from vanna.core.user import User

async def test_connection():
    # Load environment variables
    load_dotenv()

    # Initialize MySQLRunner with same config as api.py
    sql_runner = MySQLRunner(
        host=os.getenv("MYSQL_DO_HOST", "mysql-db"), 
        database=os.getenv("MYSQL_DO_DATABASE"),
        user=os.getenv("MYSQL_DO_USER"),
        password=os.getenv("MYSQL_DO_PASSWORD"),
        port=int(os.getenv("MYSQL_DO_PORT", 3306))
    )

    print("Testing MySQLRunner connection...")
    print(f"Host: {os.getenv('MYSQL_DO_HOST')}")
    print(f"Database: {os.getenv('MYSQL_DO_DATABASE')}")
    print(f"User: {os.getenv('MYSQL_DO_USER')}")
    print(f"Port: {os.getenv('MYSQL_DO_PORT')}")

    try:
        # Create a memory instance
        memory = ChromaAgentMemory(
            persist_directory="./chroma_memory",
            collection_name="test_memory"
        )
        
        # Create a context
        context = ToolContext(
            user=User(id="test_user", username="test", group_memberships=["test"]),
            conversation_id="test_connection",
            request_id="test_req_001",
            agent_memory=memory
        )
        
        # Test SHOW TABLES
        from types import SimpleNamespace
        sql_arg = SimpleNamespace(sql="SHOW TABLES")
        
        print("\nAttempting to run 'SHOW TABLES'...")
        result = await sql_runner.run_sql(sql_arg, context=context)
        
        if result is not None:
            print(f"Success! Result type: {type(result)}")
            if hasattr(result, 'empty'):
                print(f"DataFrame empty: {result.empty}")
                if not result.empty:
                    print(f"Tables found:")
                    print(result)
            else:
                print(f"Result: {result}")
        else:
            print("Result is None")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())