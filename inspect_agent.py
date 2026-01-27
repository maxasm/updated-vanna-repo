import sys
import os
from dotenv import load_dotenv
from vanna import Agent, AgentConfig
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory

load_dotenv()

from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, RequestContext, User

class DummyUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="dummy", username="dummy")

def inspect_agent():
    print("Inspecting Agent class...")
    
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    llm = OpenAILlmService(api_key=api_key, model="gpt-4o")
    memory = ChromaAgentMemory(persist_directory="./chroma_memory", collection_name="test")
    
    agent = Agent(
        llm_service=llm,
        agent_memory=memory,
        tool_registry=ToolRegistry(),
        user_resolver=DummyUserResolver(),
        config=AgentConfig(max_tool_iterations=10000)
    )
    
    print("Agent methods:")
    methods = [m for m in dir(agent) if not m.startswith('__')]
    for m in methods:
        print(f" - {m}")

if __name__ == "__main__":
    inspect_agent()
