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

async def inspect_components_deep():
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
    
    components = []
    async for component in agent.send_message(
        request_context=request_context,
        message="Show me all tables in the database",
        conversation_id="test_inspect"
    ):
        print(f"\n=== Component type: {type(component)} ===")
        
        # Convert component to dict to see all fields
        component_dict = component.dict()
        print(f"Component as dict keys: {list(component_dict.keys())}")
        
        # Check each field
        for key, value in component_dict.items():
            if value is not None:
                print(f"\n  {key}:")
                if isinstance(value, dict):
                    print(f"    {json.dumps(value, indent=4, default=str)[:200]}...")
                else:
                    print(f"    {str(value)[:200]}...")
        
        components.append(component)
    
    print(f"\nTotal components: {len(components)}")

if __name__ == "__main__":
    asyncio.run(inspect_components_deep())