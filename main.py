import os
import logging
import asyncio
from dotenv import load_dotenv
from tabulate import tabulate

# 1. Load environment variables immediately
load_dotenv()

# Vanna 2.x Imports
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.integrations.mysql import MySQLRunner
from vanna.tools import RunSqlTool
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna import Agent, AgentConfig

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [VANNA AI APP] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# --- 2. USER RESOLVER (Required for 2.x) ---
class CLIUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="admin_user", username="admin", group_memberships=["admin"])

# --- 3. INITIALIZE SERVICES ---
api_key = os.getenv("OPENAI_API_KEY")
llm = OpenAILlmService(api_key=api_key, model="gpt-5")

memory = ChromaAgentMemory(
    persist_directory="./chroma_memory",
    collection_name="tool_memories"
)

# Initialize the Runner
sql_runner = MySQLRunner(
    host=os.getenv("MYSQL_HOST", "localhost"),
    database=os.getenv("MYSQL_DB"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    port=int(os.getenv("MYSQL_PORT", 3306))
)

# --- 4. TOOL REGISTRY (Required for 2.x) ---
registry = ToolRegistry()

# FIX: Use 'sql_runner' as the argument name, not 'runner'
sql_tool = RunSqlTool(sql_runner=sql_runner)

# Register tool with access groups matching our UserResolver
registry.register_local_tool(sql_tool, access_groups=["admin"])

# --- 5. INITIALIZE AGENT ---
agent = Agent(
    llm_service=llm,
    tool_registry=registry,
    user_resolver=CLIUserResolver(),
    agent_memory=memory,
    config=AgentConfig()
)

def initial_training():
    # Check if memory has get_training_data method (legacy Vanna 1.x)
    if hasattr(memory, 'get_training_data'):
        try:
            if not memory.get_training_data().empty:
                logger.info("Memory loaded.")
                return
        except Exception as e:
            logger.warning(f"Could not check training data: {e}")
    
    # Check if memory has train method (legacy Vanna 1.x)
    if hasattr(memory, 'train'):
        logger.warning("Training on schema...")
        try:
            df_schema = sql_runner.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
            for _, row in df_schema.iterrows():
                memory.train(documentation=f"Table {row['TABLE_NAME']} has column {row['COLUMN_NAME']}")
            logger.info("Training complete.")
        except Exception as e:
            logger.error(f"Training failed: {e}")
    else:
        logger.info("Skipping training (Vanna 2.x uses different training mechanism)")

async def run_cli():
    initial_training()
    print("\n" + "="*45 + "\n   VANNA AI AGENT V2.X ONLINE\n" + "="*45)
    
    while True:
        question = input("\n💬 Question: ").strip()
        if question.lower() in ['exit', 'quit']: break
        if not question: continue

        try:
            # Create request context for CLI
            request_context = RequestContext()
            
            # send_message returns an async generator in Vanna 2.x
            response_text = ""
            response_data = None
            
            async for component in agent.send_message(request_context=request_context, message=question):
                # In a real UI, we would handle different component types
                # For CLI, we just collect text responses
                if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                    response_text += component.simple_component.text + "\n"
                # We could also check for data in the component
            
            # Print text response
            if response_text:
                print(f"\n🤖 Agent: {response_text}")
            else:
                print("\n🤖 Agent: (No text response)")
            
            # Print data if present (simplified - would need actual data extraction)
            # if response_data is not None:
            #     print("\n" + tabulate(response_data, headers='keys', tablefmt='psql', showindex=False))
                
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_cli())
