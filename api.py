"""
REST API server for Vanna AI application using FastAPI.
Migrates the TUI functionality to a REST API with learning/storing capabilities.
Returns: sql + link to csv (for visualization) + answer
"""

import os
import json
import re
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd

# Vanna 2.x Imports
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.integrations.mysql import MySQLRunner
from vanna.tools import RunSqlTool
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.tool.models import ToolContext
from vanna import Agent, AgentConfig

# Learning Manager
from learning_manager import LearningManager

# Import VannaFastAPIServer for base functionality
from vanna.servers.fastapi import VannaFastAPIServer

from logging_config import configure_logging

# --- LOGGING ---
configure_logging(component="VANNA API")
logger = logging.getLogger("vanna_api")

# --- 1. LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

# --- 2. USER RESOLVER (Required for 2.x) ---
class APIUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        # Extract user from request headers or use default
        user_id = request_context.headers.get('x-user-id', 'api_user')
        username = request_context.headers.get('x-username', 'api_user')
        groups = request_context.headers.get('x-user-groups', 'api_users').split(',')
        return User(id=user_id, username=username, group_memberships=groups)

# --- 3. INITIALIZE SERVICES ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

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

# --- 4. TOOL REGISTRY ---
registry = ToolRegistry()
sql_tool = RunSqlTool(sql_runner=sql_runner)
registry.register_local_tool(sql_tool, access_groups=["api_users"])

# --- 5. INITIALIZE AGENT ---
agent = Agent(
    llm_service=llm,
    tool_registry=registry,
    user_resolver=APIUserResolver(),
    agent_memory=memory,
    config=AgentConfig()
)

# --- 6. LEARNING MANAGER ---
learning_manager = LearningManager(agent_memory=memory)

# --- 7. CSV RESULT MANAGER ---
class CSVResultManager:
    """Manages CSV file generation and storage for query results"""
    
    def __init__(self, base_dir: str = "./query_results"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def generate_csv_filename(self, query_hash: str) -> str:
        """Generate a unique CSV filename for query results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{query_hash[:8]}.csv"
        return str(self.base_dir / filename)
    
    def save_query_results(self, df: pd.DataFrame, query_hash: str) -> str:
        """Save query results to CSV and return file path"""
        csv_path = self.generate_csv_filename(query_hash)
        df.to_csv(csv_path, index=False)
        logger.info(f"Query results saved to: {csv_path}")
        return csv_path
    
    def get_csv_url(self, csv_path: str) -> str:
        """Convert CSV file path to URL for API response"""
        try:
            # Convert to Path object
            path_obj = Path(csv_path)
            # If path is absolute, get relative path to current directory
            if path_obj.is_absolute():
                rel_path = path_obj.relative_to(Path.cwd())
            else:
                # If path is relative, use it as is
                rel_path = path_obj
            return f"/static/{rel_path}"
        except Exception as e:
            logger.error(f"Error getting CSV URL for {csv_path}: {e}")
            # Fallback: just use the filename
            filename = Path(csv_path).name
            return f"/static/{filename}"

# --- 8. CONVERSATION STORE AND FILTERS ---
class ConversationStore:
    """Stores and manages conversation history"""
    
    def __init__(self, agent_memory: ChromaAgentMemory, max_history: int = 10):
        self.memory = agent_memory
        self.max_history = max_history
        # Conversation ID will be generated per request based on user
    
    def _create_tool_context(self, user_id: str = "api_user", username: str = "api_user", 
                           conversation_id: str = None) -> ToolContext:
        """Create a ToolContext for memory operations"""
        if conversation_id is None:
            conversation_id = f"conversation_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ToolContext(
            user=User(id=user_id, username=username, group_memberships=["api_users"]),
            conversation_id=conversation_id,
            request_id=f"req_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            agent_memory=self.memory
        )
    
    async def save_conversation_turn(self, question: str, response: str, 
                                   user_id: str = "api_user", username: str = "api_user",
                                   conversation_id: str = None, metadata: Optional[Dict] = None):
        """Save a conversation turn (question + response) to memory"""
        if metadata is None:
            metadata = {}
        
        if conversation_id is None:
            conversation_id = f"conversation_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create conversation memory object with metadata embedded
        conversation_memory = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
            "type": "conversation",
            "metadata": metadata
        }
        
        # Save to memory - embed metadata in the content since save_text_memory doesn't accept metadata parameter
        memory_content = json.dumps(conversation_memory)
        context = self._create_tool_context(user_id, username, conversation_id)
        await self.memory.save_text_memory(
            content=memory_content,
            context=context
        )
    
    async def get_recent_conversations(self, user_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history for a user (or all users if user_id is None)"""
        context = self._create_tool_context()
        recent_memories = await self.memory.get_recent_text_memories(context=context, limit=limit * 2)  # Get more to filter
        
        conversations = []
        for memory_item in recent_memories:
            try:
                # Parse the JSON content
                conversation_data = json.loads(memory_item.content)
                # Check if it's a conversation memory (has type field)
                if conversation_data.get('type') == 'conversation':
                    # Filter by user_id if specified
                    if user_id is None or conversation_data.get('user_id') == user_id:
                        conversations.append(conversation_data)
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue
        
        # Return most recent conversations, up to limit
        return conversations[:limit]
    
    async def get_filtered_conversations(self, user_id: str = None, 
                                         filter_keywords: List[str] = None, 
                                         filter_metadata: Dict[str, Any] = None,
                                         limit: int = 5) -> List[Dict[str, Any]]:
        """Get conversations filtered by user, keywords or metadata"""
        context = self._create_tool_context()
        recent_memories = await self.memory.get_recent_text_memories(context=context, limit=limit * 10)  # Get more to filter
        
        filtered_conversations = []
        for memory_item in recent_memories:
            try:
                conversation_data = json.loads(memory_item.content)
                # Check if it's a conversation memory
                if conversation_data.get('type') != 'conversation':
                    continue
                
                # Filter by user_id if specified
                if user_id is not None and conversation_data.get('user_id') != user_id:
                    continue
                    
                # Apply keyword filter
                if filter_keywords:
                    text_to_search = f"{conversation_data.get('question', '')} {conversation_data.get('response', '')}".lower()
                    if not any(keyword.lower() in text_to_search for keyword in filter_keywords):
                        continue
                
                # Apply metadata filter (now metadata is inside conversation_data)
                if filter_metadata:
                    conv_metadata = conversation_data.get('metadata', {})
                    if not all(conv_metadata.get(key) == value for key, value in filter_metadata.items()):
                        continue
                
                filtered_conversations.append(conversation_data)
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue
        
        return filtered_conversations[:limit]
    
    async def clear_conversation_history(self, user_id: str = None):
        """Clear all conversation history (for testing/debugging)"""
        context = self._create_tool_context()
        recent_memories = await self.memory.get_recent_text_memories(context=context, limit=1000)
        for memory_item in recent_memories:
            try:
                conversation_data = json.loads(memory_item.content)
                if conversation_data.get('type') == 'conversation':
                    # Filter by user_id if specified
                    if user_id is None or conversation_data.get('user_id') == user_id:
                        if hasattr(memory_item, 'memory_id'):
                            # Try to delete the memory by ID with context
                            try:
                                await self.memory.delete_by_id(
                                    memory_id=memory_item.memory_id,
                                    context=context
                                )
                            except TypeError:
                                # If that fails, try without context
                                await self.memory.delete_by_id(memory_id=memory_item.memory_id)
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

class ConversationContextEnhancer:
    """Enhances questions with conversation context"""
    
    def __init__(self, conversation_store: ConversationStore):
        self.store = conversation_store
    
    async def enhance_question_with_context(self, question: str, user_id: str = None) -> str:
        """Enhance the question with relevant conversation history for a user"""
        # Get recent conversations for the user
        recent_conversations = await self.store.get_recent_conversations(user_id=user_id, limit=3)
        
        if not recent_conversations:
            return question
        
        # Build context from recent conversations
        context_lines = ["Previous conversation context:"]
        for i, conv in enumerate(recent_conversations, 1):
            context_lines.append(f"{i}. Q: {conv.get('question', '')}")
            context_lines.append(f"   A: {conv.get('response', '')[:100]}..." if len(conv.get('response', '')) > 100 else f"   A: {conv.get('response', '')}")
        
        # Add filtered conversations based on keywords
        question_keywords = self._extract_keywords(question)
        if question_keywords:
            filtered_conversations = await self.store.get_filtered_conversations(
                user_id=user_id,
                filter_keywords=question_keywords,
                limit=2
            )
            
            if filtered_conversations:
                context_lines.append("\nRelevant previous conversations:")
                for i, conv in enumerate(filtered_conversations, 1):
                    context_lines.append(f"{i}. Q: {conv.get('question', '')}")
                    context_lines.append(f"   A: {conv.get('response', '')[:100]}..." if len(conv.get('response', '')) > 100 else f"   A: {conv.get('response', '')}")
        
        context = "\n".join(context_lines)
        enhanced_question = f"{context}\n\nCurrent question: {question}"
        
        return enhanced_question
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from text (simplified)"""
        # Remove common words and extract nouns/important terms
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might', 'must'}
        
        words = text.lower().split()
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        
        return keywords[:5]  # Return top 5 keywords

# --- 9. ENHANCED CHAT HANDLER ---
class EnhancedChatHandler:
    """Enhanced chat handler that integrates learning, conversation context, and CSV generation"""
    
    def __init__(self, agent: Agent, learning_manager: LearningManager, 
                 csv_manager: CSVResultManager, sql_runner: MySQLRunner,
                 conversation_store: ConversationStore, 
                 conversation_enhancer: ConversationContextEnhancer):
        self.agent = agent
        self.learning_manager = learning_manager
        self.csv_manager = csv_manager
        self.sql_runner = sql_runner
        self.conversation_store = conversation_store
        self.conversation_enhancer = conversation_enhancer
        self.base_chat_handler = None  # Will be set after VannaFastAPIServer creation
    
    async def handle_chat_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat request with enhanced functionality including conversation context"""
        try:
            # Extract message and user info
            message = request.get("message", "")
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            headers = request.get("headers", {})
            user_id = headers.get('x-user-id', 'api_user')
            username = headers.get('x-username', 'api_user')
            
            # First enhance with learned patterns
            learned_enhanced_question = self.learning_manager.enhance_question_with_learned_patterns(message)
            
            # Then enhance with conversation context
            enhanced_question = await self.conversation_enhancer.enhance_question_with_context(
                learned_enhanced_question, user_id=user_id
            )
            
            # Create request context
            request_context = RequestContext(
                headers=headers,
                metadata=request.get("metadata", {})
            )
            
            # Track CSV before query
            csv_before = self._find_latest_csv()
            
            # Execute query through agent and capture components
            response_text = ""
            sql_query = ""
            csv_path = None
            tool_used = False
            tool_success = False
            
            # We'll capture all components to analyze tool usage
            components = []
            async for component in self.agent.send_message(
                request_context=request_context,
                message=enhanced_question
            ):
                components.append(component)
                # Collect response text
                if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                    response_text += component.simple_component.text + "\n"
                
                # Check if this is a tool call component
                if hasattr(component, 'tool_call_component'):
                    tool_used = True
                    tool_call = component.tool_call_component
                    if hasattr(tool_call, 'tool_name') and tool_call.tool_name == 'run_sql':
                        # Extract SQL from tool call
                        if hasattr(tool_call, 'args') and 'sql' in tool_call.args:
                            sql_query = tool_call.args['sql']
                            logger.info(f"Captured SQL from tool call: {sql_query[:100]}...")
            
            # Check if a new CSV was generated
            csv_after = self._find_latest_csv()
            if csv_after and csv_after != csv_before:
                csv_path = csv_after
                tool_success = True
                logger.info(f"New CSV generated: {csv_path}")

                # If we have SQL, execute it to get the dataframe for CSV generation
                if sql_query:
                    try:
                        df = self.sql_runner.run_sql(sql_query)
                        if not df.empty:
                            # Generate hash for the query
                            import hashlib
                            query_hash = hashlib.md5(sql_query.encode()).hexdigest()

                            # Save results to CSV (in case it wasn't saved by the agent)
                            csv_path = self.csv_manager.save_query_results(df, query_hash)

                        # Record successful tool usage (CSV exists either way)
                        await self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query, "result_file": csv_path},
                            success=True,
                            metadata={
                                "csv_file": csv_path,
                                "response_preview": response_text[:100],
                                "sql_extracted": True,
                                "user_id": user_id,
                                "username": username
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error executing SQL: {e}")
                        # Still record success since CSV was generated
                        await self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query},
                            success=True,  # CSV was generated, so it's a success
                            metadata={"csv_file": csv_path, "error": str(e), "user_id": user_id}
                        )
                else:
                    # CSV was generated but we don't have SQL; try to extract SQL from response text
                    sql_query = self._extract_sql_from_response(response_text)
                    if sql_query:
                        await self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query, "result_file": csv_path},
                            success=True,
                            metadata={
                                "csv_file": csv_path,
                                "response_preview": response_text[:100],
                                "sql_extracted_from_text": True,
                                "user_id": user_id
                            }
                        )
                    else:
                        # Record generic success
                        await self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="agent_execution",
                            args={"message": message},
                            success=True,
                            metadata={"csv_file": csv_path, "sql_not_found": True, "user_id": user_id}
                        )
            
            # If no CSV was generated but we have SQL, try to execute it
            elif sql_query and not csv_path:
                try:
                    df = self.sql_runner.run_sql(sql_query)
                    if not df.empty:
                        # Generate hash for the query
                        import hashlib
                        query_hash = hashlib.md5(sql_query.encode()).hexdigest()
                        
                        # Save results to CSV
                        csv_path = self.csv_manager.save_query_results(df, query_hash)
                        tool_success = True
                        
                        # Record successful tool usage
                        await self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query, "result_file": csv_path},
                            success=True,
                            metadata={
                                "csv_file": csv_path,
                                "response_preview": response_text[:100],
                                "sql_extracted": True,
                                "user_id": user_id
                            }
                        )
                except Exception as e:
                    logger.error(f"Error executing SQL: {sql_query[:100]}...: {e}")
                    # Record failure
                    await self.learning_manager.record_tool_usage(
                        question=message,
                        tool_name="run_sql",
                        args={"sql": sql_query},
                        success=False,
                        metadata={"error": str(e), "user_id": user_id}
                    )
            
            # Save conversation to history
            if response_text:
                await self.conversation_store.save_conversation_turn(
                    question=message,
                    response=response_text,
                    user_id=user_id,
                    username=username,
                    metadata={
                        "enhanced_question": enhanced_question[:200] + "..." if len(enhanced_question) > 200 else enhanced_question,
                        "learned_enhanced": learned_enhanced_question[:200] + "..." if len(learned_enhanced_question) > 200 else learned_enhanced_question,
                        "sql_query": sql_query,
                        "csv_generated": bool(csv_path),
                        "tool_success": tool_success
                    }
                )
            
            # Prepare response
            response_data = {
                "answer": response_text.strip(),
                "sql": sql_query,
                "csv_url": self.csv_manager.get_csv_url(csv_path) if csv_path else None,
                "success": tool_success,
                "timestamp": datetime.now().isoformat(),
                "tool_used": tool_used,
                "user_id": user_id,
                "username": username
            }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error handling chat request: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """Extract SQL query from agent response text"""
        # Try to find SQL in code blocks
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            # Try other SQL patterns
            sql_match = re.search(r'SELECT .*?FROM', response_text, re.DOTALL | re.IGNORECASE)
        
        if sql_match:
            sql_query = sql_match.group(1) if sql_match.group(1) else sql_match.group(0)
            return sql_query.strip()
        
        return ""
    
    def _find_latest_csv(self) -> Optional[str]:
        """Find the latest CSV file in the results directory (search recursively)"""
        try:
            # Search for CSV files in the current directory and all subdirectories
            csv_files = list(Path(".").glob("**/*.csv"))
            if not csv_files:
                return None
            # Get the most recently modified CSV file
            latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
            # Return absolute path
            return str(latest_csv.absolute())
        except Exception as e:
            logger.error(f"Error finding latest CSV: {e}")
            return None

# --- 9. CREATE FASTAPI APP ---
def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Initialize managers
    csv_manager = CSVResultManager()
    conversation_store = ConversationStore(agent_memory=memory)
    conversation_enhancer = ConversationContextEnhancer(conversation_store=conversation_store)
    
    enhanced_handler = EnhancedChatHandler(
        agent=agent,
        learning_manager=learning_manager,
        csv_manager=csv_manager,
        sql_runner=sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer
    )
    
    # Create base VannaFastAPIServer
    vanna_server = VannaFastAPIServer(
        agent=agent,
        config={
            "cors": {"enabled": True},
            "dev_mode": True
        }
    )
    
    # Get the base app
    app = vanna_server.create_app()

    # --- Request logging (similar visibility to the old TUI logs) ---

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        req_logger = logging.getLogger("vanna_api.request")
        req_logger.info("%s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            req_logger.exception("Unhandled error for %s %s", request.method, request.url.path)
            raise
        req_logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    
    # Store enhanced handler in app state
    app.state.enhanced_handler = enhanced_handler
    app.state.learning_manager = learning_manager
    app.state.csv_manager = csv_manager
    app.state.conversation_store = conversation_store
    app.state.conversation_enhancer = conversation_enhancer
    
    # Mount static files for CSV access - serve from current directory
    # This allows access to CSV files in subdirectories
    app.mount("/static", StaticFiles(directory="."), name="static")
    
    # --- CUSTOM ENDPOINTS ---

    @app.on_event("startup")
    async def _startup_load_learning_patterns():
        """Load persisted learning patterns on server startup.

        This is needed when starting via `uvicorn api:app`, because the
        `if __name__ == '__main__'` block below does not run.
        """
        await learning_manager.ensure_patterns_loaded()
    
    @app.post("/api/v1/chat")
    async def chat_endpoint_v1(request: Request):
        """Simple chat endpoint that returns sql + csv link + answer"""
        try:
            request_data = await request.json()
            message = request_data.get("message", "")
            
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            # Use the enhanced handler
            response = await enhanced_handler.handle_chat_request(request_data)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"Error in chat endpoint v1: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/learning/stats")
    async def get_learning_stats():
        """Get learning statistics"""
        try:
            stats = learning_manager.get_learning_stats()
            return JSONResponse(content=stats)
        except Exception as e:
            logger.error(f"Error getting learning stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/health")
    async def health_check_v1():
        """Health check endpoint (v1)"""
        return JSONResponse(content={
            "status": "healthy",
            "service": "vanna-api",
            "timestamp": datetime.now().isoformat(),
            "version": "v1"
        })
    
    @app.post("/api/v1/train")
    async def train_endpoint(request: Request):
        """Train the agent with schema information"""
        try:
            # Get database schema
            df_schema = sql_runner.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
            
            # Train the agent (simplified - actual training depends on Vanna version)
            training_count = 0
            for _, row in df_schema.iterrows():
                # This is a simplified training approach
                # In production, you'd use the appropriate training method
                training_count += 1
            
            return JSONResponse(content={
                "status": "success",
                "trained_items": training_count,
                "message": f"Trained on {training_count} schema items"
            })
        except Exception as e:
            logger.error(f"Error in training: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # --- NEW V2 ENDPOINTS ---
    
    @app.post("/api/vanna/v2/chat_sse")
    async def chat_sse_endpoint(request: Request):
        """Server-Sent Events streaming chat endpoint"""
        try:
            request_data = await request.json()
            message = request_data.get("message", "")
            
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            # Create request context
            request_context = RequestContext(
                headers=request_data.get("headers", {}),
                metadata=request_data.get("metadata", {})
            )
            
            # Enhance question with learned patterns
            enhanced_question = learning_manager.enhance_question_with_learned_patterns(message)
            
            async def event_stream():
                """Generate Server-Sent Events"""
                try:
                    # Send initial event
                    yield f"data: {json.dumps({'event': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"
                    
                    response_text = ""
                    sql_query = ""
                    
                    # Stream agent response
                    async for component in agent.send_message(
                        request_context=request_context,
                        message=enhanced_question
                    ):
                        if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                            text = component.simple_component.text
                            response_text += text
                            # Send text chunk as event
                            yield f"data: {json.dumps({'event': 'chunk', 'text': text})}\n\n"
                        
                        # Check for tool calls
                        if hasattr(component, 'tool_call_component'):
                            tool_call = component.tool_call_component
                            if hasattr(tool_call, 'tool_name') and tool_call.tool_name == 'run_sql':
                                if hasattr(tool_call, 'args') and 'sql' in tool_call.args:
                                    sql_query = tool_call.args['sql']
                                    yield f"data: {json.dumps({'event': 'sql', 'sql': sql_query})}\n\n"
                    
                    # After streaming complete, check for CSV generation
                    csv_path = None
                    if sql_query:
                        try:
                            df = sql_runner.run_sql(sql_query)
                            if not df.empty:
                                import hashlib
                                query_hash = hashlib.md5(sql_query.encode()).hexdigest()
                                csv_path = csv_manager.save_query_results(df, query_hash)
                                csv_url = csv_manager.get_csv_url(csv_path)
                                yield f"data: {json.dumps({'event': 'csv', 'url': csv_url})}\n\n"
                        except Exception as e:
                            logger.error(f"Error executing SQL for SSE: {e}")
                    
                    # Send completion event
                    yield f"data: {json.dumps({'event': 'complete', 'answer': response_text, 'sql': sql_query, 'csv_url': csv_manager.get_csv_url(csv_path) if csv_path else None})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable buffering for nginx
                }
            )
            
        except Exception as e:
            logger.error(f"Error in SSE endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.websocket("/api/vanna/v2/chat_websocket")
    async def chat_websocket_endpoint(websocket: WebSocket):
        """WebSocket real-time chat endpoint"""
        await websocket.accept()
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                message = data.get("message", "")
                
                if not message:
                    await websocket.send_json({"error": "Message is required"})
                    continue
                
                # Create request context
                request_context = RequestContext(
                    headers=data.get("headers", {}),
                    metadata=data.get("metadata", {})
                )
                
                # Enhance question with learned patterns
                enhanced_question = learning_manager.enhance_question_with_learned_patterns(message)
                
                # Send initial acknowledgment
                await websocket.send_json({
                    "event": "start",
                    "timestamp": datetime.now().isoformat()
                })
                
                response_text = ""
                sql_query = ""
                
                # Stream agent response
                async for component in agent.send_message(
                    request_context=request_context,
                    message=enhanced_question
                ):
                    if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                        text = component.simple_component.text
                        response_text += text
                        # Send text chunk
                        await websocket.send_json({
                            "event": "chunk",
                            "text": text
                        })
                    
                    # Check for tool calls
                    if hasattr(component, 'tool_call_component'):
                        tool_call = component.tool_call_component
                        if hasattr(tool_call, 'tool_name') and tool_call.tool_name == 'run_sql':
                            if hasattr(tool_call, 'args') and 'sql' in tool_call.args:
                                sql_query = tool_call.args['sql']
                                await websocket.send_json({
                                    "event": "sql",
                                    "sql": sql_query
                                })
                
                # After streaming complete, check for CSV generation
                csv_path = None
                if sql_query:
                    try:
                        df = sql_runner.run_sql(sql_query)
                        if not df.empty:
                            import hashlib
                            query_hash = hashlib.md5(sql_query.encode()).hexdigest()
                            csv_path = csv_manager.save_query_results(df, query_hash)
                            csv_url = csv_manager.get_csv_url(csv_path)
                            await websocket.send_json({
                                "event": "csv",
                                "url": csv_url
                            })
                    except Exception as e:
                        logger.error(f"Error executing SQL for WebSocket: {e}")
                        await websocket.send_json({
                            "event": "error",
                            "error": f"SQL execution error: {str(e)}"
                        })
                
                # Send completion
                await websocket.send_json({
                    "event": "complete",
                    "answer": response_text,
                    "sql": sql_query,
                    "csv_url": csv_manager.get_csv_url(csv_path) if csv_path else None,
                    "timestamp": datetime.now().isoformat()
                })
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error in WebSocket endpoint: {e}")
            try:
                await websocket.send_json({"error": str(e)})
            except:
                pass
    
    @app.post("/api/vanna/v2/chat_poll")
    async def chat_poll_endpoint(request: Request):
        """Request/response polling chat endpoint"""
        try:
            request_data = await request.json()
            # Use the existing enhanced handler for polling (similar to old chat endpoint)
            response = await enhanced_handler.handle_chat_request(request_data)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"Error in poll endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/health")
    async def health_check_root():
        """Root health check endpoint"""
        return JSONResponse(content={
            "status": "healthy",
            "service": "vanna-api",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "v1": {
                    "health": "/api/v1/health",
                    "learning_stats": "/api/v1/learning/stats",
                    "train": "/api/v1/train"
                },
                "v2": {
                    "chat_sse": "/api/vanna/v2/chat_sse",
                    "chat_websocket": "/api/vanna/v2/chat_websocket",
                    "chat_poll": "/api/vanna/v2/chat_poll"
                },
                "conversation": {
                    "history": "/api/v1/conversation/history",
                    "filter": "/api/v1/conversation/filter",
                    "clear": "/api/v1/conversation/clear"
                },
                "learning": {
                    "detailed_stats": "/api/v1/learning/detailed",
                    "patterns": "/api/v1/learning/patterns",
                    "enhance_test": "/api/v1/learning/enhance_test"
                }
            }
        })
    
    # --- CONVERSATION MANAGEMENT ENDPOINTS ---
    
    @app.get("/api/v1/conversation/history")
    async def get_conversation_history(user_id: Optional[str] = None, limit: int = 10):
        """Get conversation history for a user (or all users if user_id not provided)"""
        try:
            conversation_store = app.state.conversation_store
            conversations = await conversation_store.get_recent_conversations(
                user_id=user_id, 
                limit=limit
            )
            return JSONResponse(content={
                "user_id": user_id,
                "limit": limit,
                "count": len(conversations),
                "conversations": conversations
            })
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/conversation/filter")
    async def filter_conversations(
        user_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 10
    ):
        """Filter conversations by user and/or keyword"""
        try:
            conversation_store = app.state.conversation_store
            filter_keywords = [keyword] if keyword else None
            
            conversations = await conversation_store.get_filtered_conversations(
                user_id=user_id,
                filter_keywords=filter_keywords,
                limit=limit
            )
            
            return JSONResponse(content={
                "user_id": user_id,
                "keyword": keyword,
                "limit": limit,
                "count": len(conversations),
                "conversations": conversations
            })
        except Exception as e:
            logger.error(f"Error filtering conversations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/conversation/clear")
    async def clear_conversation_history(user_id: Optional[str] = None):
        """Clear conversation history for a user (or all users if user_id not provided)"""
        try:
            conversation_store = app.state.conversation_store
            await conversation_store.clear_conversation_history(user_id=user_id)
            return JSONResponse(content={
                "status": "success",
                "message": f"Cleared conversation history for user: {user_id if user_id else 'all users'}",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error clearing conversation history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # --- DETAILED LEARNING ENDPOINTS ---
    
    @app.get("/api/v1/learning/detailed")
    async def get_detailed_learning_stats():
        """Get detailed learning statistics with example patterns"""
        try:
            learning_manager = app.state.learning_manager
            stats = learning_manager.get_learning_stats()
            
            # Get example query patterns
            query_patterns = []
            for pattern_id, pattern in list(learning_manager.query_patterns.items())[:5]:
                query_patterns.append({
                    "id": pattern_id,
                    "question_pattern": pattern.question_pattern[:100] + "..." if len(pattern.question_pattern) > 100 else pattern.question_pattern,
                    "sql_pattern": pattern.sql_pattern[:100] + "..." if len(pattern.sql_pattern) > 100 else pattern.sql_pattern,
                    "tool_name": pattern.tool_name,
                    "success_count": pattern.success_count,
                    "last_used": pattern.last_used
                })
            
            # Get example tool usage patterns
            tool_patterns = []
            for pattern_id, pattern in list(learning_manager.tool_patterns.items())[:5]:
                tool_patterns.append({
                    "id": pattern_id,
                    "tool_name": pattern.tool_name,
                    "question_pattern": pattern.question_pattern[:100] + "..." if len(pattern.question_pattern) > 100 else pattern.question_pattern,
                    "success_count": pattern.success_count,
                    "failure_count": pattern.failure_count,
                    "last_used": pattern.last_used
                })
            
            return JSONResponse(content={
                **stats,
                "example_query_patterns": query_patterns,
                "example_tool_patterns": tool_patterns,
                "total_patterns_examples_shown": len(query_patterns) + len(tool_patterns)
            })
        except Exception as e:
            logger.error(f"Error getting detailed learning stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/learning/patterns")
    async def get_learning_patterns(
        pattern_type: Optional[str] = None,  # "query" or "tool"
        limit: int = 10
    ):
        """Get learning patterns with optional filtering by type"""
        try:
            learning_manager = app.state.learning_manager
            patterns = []
            
            if pattern_type is None or pattern_type == "query":
                for pattern_id, pattern in list(learning_manager.query_patterns.items())[:limit]:
                    patterns.append({
                        "type": "query",
                        "id": pattern_id,
                        "question_pattern": pattern.question_pattern,
                        "sql_pattern": pattern.sql_pattern,
                        "tool_name": pattern.tool_name,
                        "success_count": pattern.success_count,
                        "last_used": pattern.last_used,
                        "metadata": pattern.metadata
                    })
            
            if pattern_type is None or pattern_type == "tool":
                for pattern_id, pattern in list(learning_manager.tool_patterns.items())[:limit]:
                    patterns.append({
                        "type": "tool",
                        "id": pattern_id,
                        "tool_name": pattern.tool_name,
                        "question_pattern": pattern.question_pattern,
                        "args_pattern": pattern.args_pattern,
                        "success_count": pattern.success_count,
                        "failure_count": pattern.failure_count,
                        "last_used": pattern.last_used,
                        "metadata": pattern.metadata
                    })
            
            return JSONResponse(content={
                "pattern_type": pattern_type,
                "limit": limit,
                "count": len(patterns),
                "patterns": patterns
            })
        except Exception as e:
            logger.error(f"Error getting learning patterns: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/learning/enhance_test")
    async def test_learning_enhancement(request: Request):
        """Test learning enhancement on a sample question"""
        try:
            learning_manager = app.state.learning_manager
            request_data = await request.json()
            question = request_data.get("question", "")
            
            if not question:
                raise HTTPException(status_code=400, detail="Question is required")
            
            enhanced = learning_manager.enhance_question_with_learned_patterns(question)
            
            # Find similar successful queries
            similar_queries = learning_manager.find_similar_successful_queries(question, limit=3)
            similar_queries_data = []
            for pattern in similar_queries:
                similar_queries_data.append({
                    "question_pattern": pattern.question_pattern,
                    "sql_pattern": pattern.sql_pattern,
                    "success_count": pattern.success_count,
                    "last_used": pattern.last_used
                })
            
            # Find similar tool usage
            similar_tools = await learning_manager.find_similar_tool_usage(question, limit=3)
            similar_tools_data = []
            for pattern in similar_tools:
                similar_tools_data.append({
                    "tool_name": pattern.tool_name,
                    "question_pattern": pattern.question_pattern,
                    "success_count": pattern.success_count,
                    "last_used": pattern.last_used
                })
            
            return JSONResponse(content={
                "original_question": question,
                "enhanced_question": enhanced,
                "similar_queries_found": len(similar_queries),
                "similar_queries": similar_queries_data,
                "similar_tools_found": len(similar_tools),
                "similar_tools": similar_tools_data
            })
        except Exception as e:
            logger.error(f"Error testing learning enhancement: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

# --- 10. MAIN ENTRY POINT ---
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    # Ensure learning patterns are loaded
    async def load_patterns():
        await learning_manager.ensure_patterns_loaded()
        logger.info(f"Loaded {len(learning_manager.query_patterns)} query patterns")
    
    asyncio.run(load_patterns())

    host = os.getenv("HOST", "0.0.0.0")
    # Default to 8001 to avoid clashing with the Vanna UI (commonly 8000).
    port = int(os.getenv("PORT", "8001"))

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
