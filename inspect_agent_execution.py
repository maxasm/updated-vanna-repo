import asyncio
import os
import json
from dotenv import load_dotenv
from vanna import Agent, AgentConfig
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, RequestContext, User
from vanna.tools import RunSqlTool
from vanna.integrations.mysql import MySQLRunner

load_dotenv()

class DummyUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="dummy", username="dummy")

async def inspect_agent_execution():
    print("Setting up agent...")
    
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    llm = OpenAILlmService(api_key=api_key, model="gpt-4o")
    memory = ChromaAgentMemory(persist_directory="./chroma_memory", collection_name="test")
    
    # Initialize SQL runner
    sql_runner = MySQLRunner(
        host=os.getenv("MYSQL_DO_HOST", "mysql-db"), 
        database=os.getenv("MYSQL_DO_DATABASE"),
        user=os.getenv("MYSQL_DO_USER"),
        password=os.getenv("MYSQL_DO_PASSWORD"),
        port=int(os.getenv("MYSQL_DO_PORT", 3306))
    )
    
    # Create tool registry
    registry = ToolRegistry()
    sql_tool = RunSqlTool(sql_runner=sql_runner)
    registry.register_local_tool(sql_tool, access_groups=["api_users"])
    
    agent = Agent(
        llm_service=llm,
        agent_memory=memory,
        tool_registry=registry,
        user_resolver=DummyUserResolver(),
        config=AgentConfig(max_tool_iterations=10000)
    )
    
    print("Sending message to agent...")
    
    request_context = RequestContext(headers={}, metadata={})
    
    # Collect all components
    all_components = []
    response_text = ""
    
    async for component in agent.send_message(
        request_context=request_context,
        message="Show me all tables in the database",
        conversation_id="test_inspect"
    ):
        all_components.append(component)
        
        # Check component structure
        comp_dict = component.model_dump()
        
        # Look for any tool-related information
        if comp_dict.get('rich_component'):
            rich = comp_dict['rich_component']
            if isinstance(rich, dict):
                # Check if this looks like a tool call
                if 'type' in rich and ('tool' in rich['type'].lower() or 'sql' in rich['type'].lower()):
                    print(f"Found potential tool component: {json.dumps(rich, indent=2)[:500]}")
        
        if comp_dict.get('simple_component'):
            simple = comp_dict['simple_component']
            if isinstance(simple, dict) and simple.get('text'):
                text = simple['text']
                response_text += text + "\n"
                # Check if text contains SQL
                if 'SELECT' in text.upper() or 'SHOW' in text.upper():
                    print(f"Found SQL in text: {text[:200]}")
    
    print(f"\nTotal components collected: {len(all_components)}")
    print(f"\nFinal response text:\n{response_text[:500]}...")
    
    # Check if any CSV files were created
    import glob
    csv_files = glob.glob("**/*.csv", recursive=True)
    print(f"\nCSV files found: {len(csv_files)}")
    for csv in csv_files[:5]:
        print(f"  - {csv}")
    
    # Try to get conversation memory
    print("\nTrying to get conversation memory...")
    try:
        # Get recent memories for this conversation
        from vanna.core.tool.models import ToolContext
        context = ToolContext(
            user=User(id="dummy", username="dummy"),
            conversation_id="test_inspect",
            request_id="test_request",
            agent_memory=memory
        )
        
        memories = await memory.get_recent_text_memories(context=context, limit=10)
        print(f"Found {len(memories)} memories")
        for i, mem in enumerate(memories):
            print(f"Memory {i}: {mem.content[:200]}...")
    except Exception as e:
        print(f"Error getting memories: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_agent_execution())