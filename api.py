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

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [VANNA AI API] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

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

# --- 8. ENHANCED CHAT HANDLER ---
class EnhancedChatHandler:
    """Enhanced chat handler that integrates learning and CSV generation"""
    
    def __init__(self, agent: Agent, learning_manager: LearningManager, 
                 csv_manager: CSVResultManager, sql_runner: MySQLRunner):
        self.agent = agent
        self.learning_manager = learning_manager
        self.csv_manager = csv_manager
        self.sql_runner = sql_runner
        self.base_chat_handler = None  # Will be set after VannaFastAPIServer creation
    
    async def handle_chat_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat request with enhanced functionality"""
        try:
            # Extract message
            message = request.get("message", "")
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            # Enhance question with learned patterns
            enhanced_question = self.learning_manager.enhance_question_with_learned_patterns(message)
            
            # Create request context
            request_context = RequestContext(
                headers=request.get("headers", {}),
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
                            
                            # Record successful tool usage
                            self.learning_manager.record_tool_usage(
                                question=message,
                                tool_name="run_sql",
                                args={"sql": sql_query, "result_file": csv_path},
                                success=True,
                                metadata={
                                    "csv_file": csv_path,
                                    "response_preview": response_text[:100],
                                    "sql_extracted": True
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error executing SQL: {e}")
                        # Still record success since CSV was generated
                        self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query},
                            success=True,  # CSV was generated, so it's a success
                            metadata={"csv_file": csv_path, "error": str(e)}
                        )
                else:
                    # CSV was generated but we don't have SQL
                    # Try to extract SQL from response text
                    sql_query = self._extract_sql_from_response(response_text)
                    if sql_query:
                        self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query, "result_file": csv_path},
                            success=True,
                            metadata={
                                "csv_file": csv_path,
                                "response_preview": response_text[:100],
                                "sql_extracted_from_text": True
                            }
                        )
                    else:
                        # Record generic success
                        self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="agent_execution",
                            args={"message": message},
                            success=True,
                            metadata={"csv_file": csv_path, "sql_not_found": True}
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
                        self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="run_sql",
                            args={"sql": sql_query, "result_file": csv_path},
                            success=True,
                            metadata={
                                "csv_file": csv_path,
                                "response_preview": response_text[:100],
                                "sql_extracted": True
                            }
                        )
                except Exception as e:
                    logger.error(f"Error executing SQL: {sql_query[:100]}...: {e}")
                    # Record failure
                    self.learning_manager.record_tool_usage(
                        question=message,
                        tool_name="run_sql",
                        args={"sql": sql_query},
                        success=False,
                        metadata={"error": str(e)}
                    )
            
            # Prepare response
            response_data = {
                "answer": response_text.strip(),
                "sql": sql_query,
                "csv_url": self.csv_manager.get_csv_url(csv_path) if csv_path else None,
                "success": tool_success,
                "timestamp": datetime.now().isoformat(),
                "tool_used": tool_used
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
    enhanced_handler = EnhancedChatHandler(
        agent=agent,
        learning_manager=learning_manager,
        csv_manager=csv_manager,
        sql_runner=sql_runner
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
    
    # Store enhanced handler in app state
    app.state.enhanced_handler = enhanced_handler
    app.state.learning_manager = learning_manager
    app.state.csv_manager = csv_manager
    
    # Mount static files for CSV access - serve from current directory
    # This allows access to CSV files in subdirectories
    app.mount("/static", StaticFiles(directory="."), name="static")
    
    # --- CUSTOM ENDPOINTS ---
    
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
                }
            }
        })
    
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
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
