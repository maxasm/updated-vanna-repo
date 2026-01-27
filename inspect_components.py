import asyncio
import os
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

async def inspect_components():
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
        print(f"Component attributes: {[attr for attr in dir(component) if not attr.startswith('__')]}")
        
        # Check for specific attributes
        if hasattr(component, 'simple_component'):
            print(f"Has simple_component: {component.simple_component}")
            if hasattr(component.simple_component, 'text'):
                print(f"Text: {component.simple_component.text}")
        
        if hasattr(component, 'tool_call_component'):
            print(f"Has tool_call_component: {component.tool_call_component}")
            tool_call = component.tool_call_component
            print(f"Tool call attributes: {[attr for attr in dir(tool_call) if not attr.startswith('__')]}")
            if hasattr(tool_call, 'tool_name'):
                print(f"Tool name: {tool_call.tool_name}")
            if hasattr(tool_call, 'args'):
                print(f"Args: {tool_call.args}")
        
        if hasattr(component, 'tool_result_component'):
            print(f"Has tool_result_component: {component.tool_result_component}")
            tool_result = component.tool_result_component
            print(f"Tool result attributes: {[attr for attr in dir(tool_result) if not attr.startswith('__')]}")
        
        components.append(component)
    
    print(f"\nTotal components: {len(components)}")

if __name__ == "__main__":
    asyncio.run(inspect_components())