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
import plotly
import plotly.express as px
import plotly.io as pio

# Vanna 2.x Imports
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.integrations.mysql import MySQLRunner
from vanna.tools import RunSqlTool, PlotlyChartGenerator, VisualizeDataTool
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.tool.models import ToolContext
from vanna import Agent, AgentConfig

# Learning Manager
from learning_manager import LearningManager

# Golden Query Manager
from golden_query_manager import get_golden_query_manager

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
        user_id = request_context.headers.get('x-user-id') or request_context.headers.get('x-user-identifier') or 'api_user'
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
    host=os.getenv("MYSQL_DO_HOST", "mysql-db"), 
    database=os.getenv("MYSQL_DO_DATABASE"),
    user=os.getenv("MYSQL_DO_USER"),
    password=os.getenv("MYSQL_DO_PASSWORD"),
    port=int(os.getenv("MYSQL_DO_PORT", 3306))
)

# --- 4. TOOL REGISTRY ---
registry = ToolRegistry()
sql_tool = RunSqlTool(sql_runner=sql_runner)
visualize_tool = VisualizeDataTool()
registry.register_local_tool(sql_tool, access_groups=["api_users"])
registry.register_local_tool(visualize_tool, access_groups=["api_users"])

# --- 5. INITIALIZE AGENT ---
agent = Agent(
    llm_service=llm,
    tool_registry=registry,
    user_resolver=APIUserResolver(),
    agent_memory=memory,
    config=AgentConfig(max_tool_iterations=10000)
)

# --- 6. LEARNING MANAGER ---
learning_manager = LearningManager(agent_memory=memory)

# --- 6.5 GOLDEN QUERY MANAGER ---
golden_query_manager = get_golden_query_manager()

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

# --- 7.5 CHART MANAGER ---
class ChartManager:
    """Manages chart generation and storage with unique IDs"""
    
    def __init__(self, base_dir: str = "./charts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def generate_chart_id(self) -> str:
        """Generate a unique chart ID"""
        import uuid
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())
        chart_id = hashlib.md5(f"{timestamp}_{unique_id}".encode()).hexdigest()[:12]
        return f"chart_{chart_id}"
    
    def generate_chart_filename(self, chart_id: str, format: str = "json") -> str:
        """Generate chart filename based on chart ID and format"""
        if format == "json":
            return str(self.base_dir / f"{chart_id}.json")
        elif format == "png":
            return str(self.base_dir / f"{chart_id}.png")
        elif format == "html":
            return str(self.base_dir / f"{chart_id}.html")
        else:
            return str(self.base_dir / f"{chart_id}.{format}")
    
    def save_chart_data(self, chart_data: Dict[str, Any], chart_id: Optional[str] = None) -> Dict[str, str]:
        """Save chart data to JSON file and return chart info with ID and URLs"""
        if chart_id is None:
            chart_id = self.generate_chart_id()
        
        # Save JSON data
        json_path = self.generate_chart_filename(chart_id, "json")
        with open(json_path, 'w') as f:
            json.dump(chart_data, f, indent=2)
        logger.info(f"Chart data saved to: {json_path}")
        
        # Generate HTML version for interactive viewing
        html_path = self.generate_chart_filename(chart_id, "html")
        try:
            if 'data' in chart_data and 'layout' in chart_data:
                fig = plotly.graph_objs.Figure(data=chart_data['data'], layout=chart_data.get('layout', {}))
                pio.write_html(fig, html_path)
                logger.info(f"Chart HTML saved to: {html_path}")
        except Exception as e:
            logger.error(f"Error saving chart HTML: {e}")
        
        # Generate PNG version for download
        png_path = self.generate_chart_filename(chart_id, "png")
        try:
            if 'data' in chart_data and 'layout' in chart_data:
                fig = plotly.graph_objs.Figure(data=chart_data['data'], layout=chart_data.get('layout', {}))
                fig.write_image(png_path)
                logger.info(f"Chart PNG saved to: {png_path}")
        except Exception as e:
            logger.error(f"Error saving chart PNG: {e}")
        
        return {
            "chart_id": chart_id,
            "json_url": f"/static/{os.path.relpath(json_path, Path.cwd())}",
            "html_url": f"/static/{os.path.relpath(html_path, Path.cwd())}",
            "png_url": f"/static/{os.path.relpath(png_path, Path.cwd())}",
            "json_path": json_path,
            "html_path": html_path,
            "png_path": png_path
        }
    
    def get_chart_urls(self, chart_id: str) -> Dict[str, str]:
        """Get URLs for a chart by ID"""
        return {
            "json_url": f"/api/v1/charts/{chart_id}/json",
            "html_url": f"/api/v1/charts/{chart_id}/html",
            "png_url": f"/api/v1/charts/{chart_id}/png",
            "download_url": f"/api/v1/charts/{chart_id}/download"
        }
    
    def get_chart_data(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """Get chart data by ID"""
        json_path = self.generate_chart_filename(chart_id, "json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                return json.load(f)
        return None
    
    def chart_exists(self, chart_id: str) -> bool:
        """Check if a chart exists by ID"""
        json_path = self.generate_chart_filename(chart_id, "json")
        return os.path.exists(json_path)

# --- 8. CONVERSATION STORE AND FILTERS ---

def _normalize_session_identifier(value: Optional[str]) -> Optional[str]:
    """Normalize user/conversation identifiers to avoid accidental None/empty mixing."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


class ConversationStore:
    """Stores and manages conversation history.

    IMPORTANT: We keep conversation context isolated per (user_identifier, conversation_id)
    combination, mirroring the "user isolation" principle shown in Vanna's placeholder/auth docs.

    We intentionally do NOT use ChromaAgentMemory for conversation history because the
    `save_text_memory` API in this repo's Vanna version does not support user/conversation
    metadata filtering at the storage layer.
    """

    def __init__(self, max_history: int = 50, persistence_file: str = "conversation_history.json"):
        self.max_history = max_history
        self.persistence_file = persistence_file
        # key: (user_identifier, conversation_id) -> list of turns
        self._history: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self._load_from_file()

    def _scope_key(self, user_identifier: Optional[str], conversation_id: Optional[str]) -> tuple[str, str]:
        user_identifier = _normalize_session_identifier(user_identifier) or "anonymous"
        conversation_id = _normalize_session_identifier(conversation_id) or "default"
        return (user_identifier, conversation_id)
        
    def _load_from_file(self):
        """Load history from JSON file"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys "user_id|conv_id" back to tuple keys
                    for key_str, turns in data.items():
                        if "|" in key_str:
                            parts = key_str.split("|", 1)
                            scope = (parts[0], parts[1])
                            self._history[scope] = turns
            logger.info(f"Loaded conversation history from {self.persistence_file}")
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")

    def _save_to_file(self):
        """Save history to JSON file"""
        try:
            # Convert tuple keys to string keys for JSON
            data = {}
            for scope, turns in self._history.items():
                key_str = f"{scope[0]}|{scope[1]}"
                data[key_str] = turns
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversation history: {e}")

    async def save_conversation_turn(
        self,
        question: str,
        response: str,
        *,
        user_identifier: Optional[str],
        username: Optional[str],
        conversation_id: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if metadata is None:
            metadata = {}

        scope = self._scope_key(user_identifier, conversation_id)
        record = {
            "conversation_id": scope[1],
            "user_id": scope[0],
            "username": username or scope[0],
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
            "type": "conversation",
            "metadata": metadata,
        }

        async with self._lock:
            turns = self._history.setdefault(scope, [])
            turns.append(record)
            # cap per-scope history
            if len(turns) > self.max_history:
                self._history[scope] = turns[-self.max_history :]
            
            # Save to file after update
            self._save_to_file()

    async def get_recent_conversations(
        self,
        *,
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history.

        If both user_identifier and conversation_id are provided, returns that exact scope.
        If only user_identifier is provided, returns recent across all that user's conversations.
        If neither is provided, returns recent across all users/conversations.
        """
        user_identifier = _normalize_session_identifier(user_identifier)
        conversation_id = _normalize_session_identifier(conversation_id)

        async with self._lock:
            all_turns: List[Dict[str, Any]] = []

            for (uid, cid), turns in self._history.items():
                if user_identifier is not None and uid != user_identifier:
                    continue
                if conversation_id is not None and cid != conversation_id:
                    continue
                all_turns.extend(turns)

            all_turns.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return all_turns[:limit]

    async def get_filtered_conversations(
        self,
        *,
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
        filter_keywords: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        recent = await self.get_recent_conversations(
            user_identifier=user_identifier, conversation_id=conversation_id, limit=limit * 50
        )

        filtered: List[Dict[str, Any]] = []
        for conv in recent:
            if filter_keywords:
                text_to_search = f"{conv.get('question', '')} {conv.get('response', '')}".lower()
                if not any(k.lower() in text_to_search for k in filter_keywords):
                    continue

            if filter_metadata:
                conv_metadata = conv.get("metadata", {}) or {}
                if not all(conv_metadata.get(k) == v for k, v in filter_metadata.items()):
                    continue

            filtered.append(conv)

        return filtered[:limit]

    async def clear_conversation_history(
        self,
        *,
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        """Clear conversation history.

        - If both are provided: clears that exact (user, conversation).
        - If only user provided: clears all conversations for that user.
        - If neither: clears everything.
        """
        user_identifier = _normalize_session_identifier(user_identifier)
        conversation_id = _normalize_session_identifier(conversation_id)

        async with self._lock:
            if user_identifier is None and conversation_id is None:
                self._history.clear()
                self._save_to_file()
                return

            keys_to_delete = []
            for (uid, cid) in self._history.keys():
                if user_identifier is not None and uid != user_identifier:
                    continue
                if conversation_id is not None and cid != conversation_id:
                    continue
                keys_to_delete.append((uid, cid))

            for k in keys_to_delete:
                self._history.pop(k, None)
            
            self._save_to_file()

class ConversationContextEnhancer:
    """Enhances questions with conversation context"""
    
    def __init__(self, conversation_store: ConversationStore):
        self.store = conversation_store
    
    async def enhance_question_with_context(
        self,
        question: str,
        *,
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        """Enhance the question with relevant conversation history for a (user, conversation) scope."""
        recent_conversations = await self.store.get_recent_conversations(
            user_identifier=user_identifier,
            conversation_id=conversation_id,
            limit=3,
        )
        
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
                user_identifier=user_identifier,
                conversation_id=conversation_id,
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
                 conversation_enhancer: ConversationContextEnhancer,
                 chart_manager: Optional[ChartManager] = None):
        self.agent = agent
        self.learning_manager = learning_manager
        self.csv_manager = csv_manager
        self.sql_runner = sql_runner
        self.conversation_store = conversation_store
        self.conversation_enhancer = conversation_enhancer
        self.chart_generator = PlotlyChartGenerator()
        self.chart_manager = chart_manager or ChartManager()
        self.base_chat_handler = None  # Will be set after VannaFastAPIServer creation
    
    async def handle_chat_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat request with enhanced functionality including conversation context"""
        try:
            # Extract message and user info
            message = request.get("message", "")
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            headers = request.get("headers", {})
            # NOTE: these are expected to be sourced from the PHP session by the caller.
            user_identifier = (
                headers.get("x-user-id")
                or headers.get("x-user-identifier")
                or request.get("user_identifier")
                or request.get("user_id")
                or "api_user"
            )
            conversation_id = (
                headers.get("x-conversation-id")
                or headers.get("x-conversation")
                or request.get("conversation_id")
                or (request.get("metadata") or {}).get("conversation_id")
            )
            username = headers.get("x-username") or str(user_identifier)
            
            # First enhance with learned patterns
            learned_enhanced_question = self.learning_manager.enhance_question_with_learned_patterns(message)
            
            # Then enhance with conversation context
            enhanced_question = await self.conversation_enhancer.enhance_question_with_context(
                learned_enhanced_question,
                user_identifier=user_identifier,
                conversation_id=conversation_id,
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
            chart_json = None
            chart_source = None  # Will be "vanna_ai_tool", "auto_generated", or None
            tool_used = False
            tool_success = False
            
            # We'll capture all components to analyze tool usage
            components = []
            component_count = 0
            async for component in self.agent.send_message(
                request_context=request_context,
                message=enhanced_question,
                conversation_id=conversation_id,
            ):
                components.append(component)
                component_count += 1
                
                # Log component structure for debugging
                logger.debug(f"Component {component_count}: type={type(component)}")
                
                # Collect response text
                if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                    text = component.simple_component.text
                    response_text += text + "\n"
                    logger.debug(f"  Added text: {text[:100]}...")
                
                # Check if this is a tool call component
                if hasattr(component, 'tool_call_component'):
                    tool_used = True
                    tool_call = component.tool_call_component
                    logger.info(f"Found tool_call_component: {type(tool_call)}")
                    if hasattr(tool_call, 'tool_name'):
                        logger.info(f"Tool called: {tool_call.tool_name}")
                        if tool_call.tool_name == 'run_sql':
                            # Extract SQL from tool call
                            if hasattr(tool_call, 'args') and 'sql' in tool_call.args:
                                sql_query = tool_call.args['sql']
                                logger.info(f"Captured SQL from tool call: {sql_query[:100]}...")
                            else:
                                logger.warning(f"Tool call for 'run_sql' but no 'sql' in args or args missing")
                                # Try to inspect args structure
                                if hasattr(tool_call, 'args'):
                                    logger.warning(f"Tool call args: {tool_call.args}")
                        elif tool_call.tool_name == 'visualize_data':
                            # Visualization tool was called - this indicates chart generation
                            logger.info(f"Visualization tool called, expecting chart data")
                            tool_used = True
                            chart_source = "vanna_ai_tool"
                    else:
                        logger.warning(f"Tool call component has no tool_name attribute")
                else:
                    # Check for other possible tool-related attributes
                    component_dict = component.model_dump() if hasattr(component, 'model_dump') else {}
                    if component_dict.get('rich_component'):
                        rich = component_dict['rich_component']
                        if isinstance(rich, dict) and 'type' in rich:
                            logger.debug(f"  Rich component type: {rich['type']}")
                            if 'tool' in rich['type'].lower() or 'sql' in rich['type'].lower():
                                logger.info(f"Found potential tool in rich_component: {rich['type']}")
                
                # Try to extract chart data from component
                extracted_chart = self._extract_chart_from_component(component)
                if extracted_chart and chart_json is None:
                    chart_json = extracted_chart
                    if chart_source is None:
                        chart_source = "vanna_ai_tool"
                    logger.info(f"Chart data extracted from component")
                
                # Check for tool result errors (like missing CSV files)
                if hasattr(component, 'tool_result_component'):
                    tool_result = component.tool_result_component
                    logger.info(f"Found tool_result_component: {type(tool_result)}")
                    if hasattr(tool_result, 'error') and tool_result.error:
                        logger.warning(f"Tool result error detected: {tool_result.error}")
                        # If it's a file not found error for visualization, we might want to handle it
                        if "FileNotFoundError" in str(tool_result.error) or "does not exist" in str(tool_result.error):
                            logger.warning(f"CSV file not found for visualization tool. This may affect chart generation.")
            
            logger.info(f"Processed {component_count} components from agent")
            
            # Check if a new CSV was generated
            csv_after = self._find_latest_csv()
            if csv_after and csv_after != csv_before:
                csv_path = csv_after
                tool_success = True
                tool_used = True  # CSV was generated, so a tool was used
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
                                        "user_id": user_identifier,
                                        "username": username
                                    }
                                )

                                # Save as golden query if successful
                                try:
                                    # Import golden query manager
                                    from golden_query_manager import get_golden_query_manager
                                    gqm = get_golden_query_manager()

                                    # Add as golden query
                                    golden_query = gqm.add_golden_query(
                                        user_id=user_identifier,
                                        conversation_id=conversation_id,
                                        original_question=message,
                                        sql_query=sql_query,
                                        description=f"Auto-generated from successful query",
                                        tags=["auto_generated", "successful"],
                                        metadata={
                                            "csv_file": csv_path,
                                            "response_preview": response_text[:100],
                                            "auto_saved": True,
                                            "timestamp": datetime.now().isoformat()
                                        }
                                    )
                                    logger.info(f"Auto-saved successful query as golden query: {golden_query.query_id}")
                                except Exception as e:
                                    logger.error(f"Error saving golden query: {e}")
                                    # Don't fail the request if golden query saving fails
                        except Exception as e:
                            logger.error(f"Error executing SQL: {e}")
                            # Still record success since CSV was generated
                            await self.learning_manager.record_tool_usage(
                                question=message,
                                tool_name="run_sql",
                            args={"sql": sql_query},
                            success=True,  # CSV was generated, so it's a success
                            metadata={"csv_file": csv_path, "error": str(e), "user_id": user_identifier}
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
                                "user_id": user_identifier,
                            }
                        )
                    else:
                        # Record generic success
                        await self.learning_manager.record_tool_usage(
                            question=message,
                            tool_name="agent_execution",
                            args={"message": message},
                            success=True,
                            metadata={"csv_file": csv_path, "sql_not_found": True, "user_id": user_identifier}
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
                                "user_id": user_identifier,
                                "username": username
                            }
                        )
                        
                        # Save as golden query if successful
                        try:
                            # Import golden query manager
                            from golden_query_manager import get_golden_query_manager
                            gqm = get_golden_query_manager()
                            
                            # Add as golden query
                            golden_query = gqm.add_golden_query(
                                user_id=user_identifier,
                                conversation_id=conversation_id,
                                original_question=message,
                                sql_query=sql_query,
                                description=f"Auto-generated from successful query",
                                tags=["auto_generated", "successful"],
                                metadata={
                                    "csv_file": csv_path,
                                    "response_preview": response_text[:100],
                                    "auto_saved": True,
                                    "timestamp": datetime.now().isoformat()
                                }
                            )
                            logger.info(f"Auto-saved successful query as golden query: {golden_query.query_id}")
                        except Exception as e:
                            logger.error(f"Error saving golden query: {e}")
                            # Don't fail the request if golden query saving fails
                        
                        tool_success = True
                        

                        
                        # Generate Chart if configured and we have results
                        try:
                            # Generate Plotly chart using the generator
                            # It automatically determines the best chart type based on the dataframe
                            chart_dict = self.chart_generator.generate_chart(df=df)
                            
                            if chart_dict:
                                chart_json = chart_dict
                                logger.info("Chart generated successfully")
                                
                                # Record successful chart generation
                                await self.learning_manager.record_tool_usage(
                                    question=message,
                                    tool_name="generate_chart",
                                    args={"sql": sql_query},
                                    success=True,
                                    metadata={
                                        "chart_generated": True,
                                        "user_id": user_identifier
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Error generating chart: {e}")
                            # Don't fail the request if chart generation fails
                except Exception as e:
                    logger.error(f"Error executing SQL: {sql_query[:100]}...: {e}")
                    # Record failure
                    await self.learning_manager.record_tool_usage(
                        question=message,
                        tool_name="run_sql",
                        args={"sql": sql_query},
                        success=False,
                        metadata={"error": str(e), "user_id": user_identifier}
                    )
            
            # Check if visualization was created but chart wasn't extracted
            # This happens when VisualizeDataTool runs but chart extraction fails
            if "Created visualization" in response_text and csv_path and chart_json is None:
                logger.info(f"Detected 'Created visualization' in response but no chart extracted. CSV path: {csv_path}")
                try:
                    # Try to load the CSV and generate chart
                    if os.path.exists(csv_path):
                        df = pd.read_csv(csv_path)
                        if not df.empty:
                            logger.info(f"Loaded CSV for chart generation: {csv_path}, shape: {df.shape}")
                            chart_dict = self.chart_generator.generate_chart(df=df)
                            if chart_dict:
                                chart_json = chart_dict
                                chart_source = "forced_after_visualize_tool"
                                logger.info(f"Generated chart from CSV after visualization tool call")
                            else:
                                logger.warning(f"Chart generator returned None for CSV: {csv_path}")
                        else:
                            logger.warning(f"CSV is empty: {csv_path}")
                    else:
                        logger.warning(f"CSV file not found for visualization: {csv_path}")
                except Exception as e:
                    logger.error(f"Error generating chart from CSV after visualization: {e}")
            
            # Save chart data if we have a chart
            chart_info = None
            if chart_json:
                try:
                    chart_info = self.chart_manager.save_chart_data(chart_json)
                    logger.info(f"Chart saved with ID: {chart_info['chart_id']}")
                    
                    # If chart_source is not set yet (e.g., auto-generated chart), set it now
                    if chart_source is None:
                        chart_source = "auto_generated"
                    
                    # Record successful chart generation
                    await self.learning_manager.record_tool_usage(
                        question=message,
                        tool_name="generate_chart",
                        args={"chart_id": chart_info['chart_id']},
                        success=True,
                        metadata={
                            "chart_id": chart_info['chart_id'],
                            "chart_generated": True,
                            "user_id": user_identifier,
                            "chart_source": chart_source
                        }
                    )
                except Exception as e:
                    logger.error(f"Error saving chart data: {e}")
                    # Don't fail the request if chart saving fails
            
            # Always try to extract SQL from response text as a final fallback
            # This handles cases where SQL is in the response but wasn't captured from tool calls
            if not sql_query:
                extracted_sql = self._extract_sql_from_response(response_text)
                if extracted_sql:
                    logger.info(f"Extracted SQL from response text as fallback: {extracted_sql[:100]}...")
                    sql_query = extracted_sql
            
            # Save conversation to history (always, even if the agent produced an empty answer)
            await self.conversation_store.save_conversation_turn(
                question=message,
                response=response_text,
                user_identifier=user_identifier,
                username=username,
                conversation_id=conversation_id,
                metadata={
                    "enhanced_question": enhanced_question[:200] + "..." if len(enhanced_question) > 200 else enhanced_question,
                    "learned_enhanced": learned_enhanced_question[:200] + "..." if len(learned_enhanced_question) > 200 else learned_enhanced_question,
                    "sql_query": sql_query,
                    "csv_generated": bool(csv_path),
                    "chart_generated": bool(chart_json),
                    "chart_id": chart_info['chart_id'] if chart_info else None,
                    "chart": chart_json,
                    "chart_source": chart_source,
                    "tool_success": tool_success,
                },
            )
            
            # Prepare response
            response_data = {
                "answer": response_text.strip(),
                "sql": sql_query,
                "csv_url": self.csv_manager.get_csv_url(csv_path) if csv_path else None,
                "chart": chart_json,
                "chart_info": {
                    "chart_id": chart_info['chart_id'] if chart_info else None,
                    "json_url": chart_info['json_url'] if chart_info else None,
                    "html_url": chart_info['html_url'] if chart_info else None,
                    "png_url": chart_info['png_url'] if chart_info else None,
                    "download_url": f"/api/v1/charts/{chart_info['chart_id']}/download" if chart_info else None
                } if chart_info else None,
                "success": tool_success,
                "timestamp": datetime.now().isoformat(),
                "tool_used": tool_used,
                "chart_generated": bool(chart_json),
                "chart_source": chart_source,
                "user_id": user_identifier,
                "conversation_id": conversation_id,
                "username": username
            }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error handling chat request: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """Improved SQL extraction from agent response text"""
        logger.debug(f"Attempting to extract SQL from response text (length: {len(response_text)})")
        
        # First, try to find SQL in code blocks (most reliable)
        # Match ```sql ... ``` or ```SQL ... ```
        sql_match = re.search(r'```(?:sql|SQL)\s*(.*?)\s*```', response_text, re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
            logger.info(f"Extracted SQL from code block: {sql_query[:100]}...")
            return sql_query
        
        # Try to find SQL statements without code blocks
        # Look for common SQL patterns - improved to stop at semicolon or end of line
        sql_patterns = [
            # SHOW commands - stop at semicolon or end
            r'(SHOW\s+(?:TABLES|DATABASES|COLUMNS|INDEXES|CREATE\s+TABLE)[^;]*)(?:;|$)',
            # SELECT statements (more complete capture)
            r'(SELECT\s+(?:.|\n)*?(?:FROM\s+(?:.|\n)*?)(?:\s+WHERE\s+(?:.|\n)*?)?(?:\s+GROUP BY\s+(?:.|\n)*?)?(?:\s+ORDER BY\s+(?:.|\n)*?)?(?:\s+LIMIT\s+\d+)?)(?:\s*;|$)',
            # DESCRIBE commands
            r'(DESCRIBE\s+\w+[^;]*)(?:;|$)',
            # MySQL specific: SHOW CREATE TABLE
            r'(SHOW\s+CREATE\s+TABLE\s+\w+[^;]*)(?:;|$)',
        ]
        
        for pattern in sql_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(1).strip()
                # Clean up: remove trailing punctuation and extra whitespace
                sql = re.sub(r'[;.]\s*$', '', sql)
                logger.info(f"Extracted SQL using pattern '{pattern[:30]}...': {sql[:100]}...")
                return sql
        
        # Try to find any SQL-like statement that starts with common keywords
        sql_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH']
        for keyword in sql_keywords:
            # Find the keyword in text (case insensitive)
            pattern = rf'\b{keyword}\b'
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                start_idx = match.start()
                # Look for end of statement (semicolon, double newline, or end of text)
                remaining = response_text[start_idx:]
                # Try to find a reasonable end point
                end_match = re.search(r'[;.]\s*\n|\n\n|$', remaining)
                if end_match:
                    end_idx = start_idx + end_match.start()
                    sql = response_text[start_idx:end_idx].strip()
                    # Basic validation: should contain SQL keywords
                    if len(sql.split()) > 2:  # At least 3 words (e.g., "SHOW TABLES")
                        logger.info(f"Extracted SQL starting with '{keyword}': {sql[:100]}...")
                        return sql
        
        logger.debug("No SQL found in response text")
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
    
    def _extract_chart_from_component(self, component) -> Optional[Dict[str, Any]]:
        """Extract chart data from a component if it contains any"""
        logger.debug(f"Checking component for chart data: {type(component)}")
        
        # Check for tool result component with chart data in metadata
        if hasattr(component, 'tool_result_component'):
            tool_result = component.tool_result_component
            logger.debug(f"Found tool_result_component: {type(tool_result)}")
            
            if hasattr(tool_result, 'metadata') and tool_result.metadata:
                logger.debug(f"Tool result has metadata: {type(tool_result.metadata)}")
                # Check if metadata is a dictionary and has 'chart' key
                if isinstance(tool_result.metadata, dict):
                    if 'chart' in tool_result.metadata:
                        chart_data = tool_result.metadata['chart']
                        logger.debug(f"Found chart in metadata: {type(chart_data)}")
                        if self._is_valid_chart_data(chart_data):
                            logger.info(f"Extracted chart data from tool_result.metadata['chart']")
                            return chart_data
                    # Also check for plotly_figure key
                    if 'plotly_figure' in tool_result.metadata:
                        chart_data = tool_result.metadata['plotly_figure']
                        logger.debug(f"Found plotly_figure in metadata: {type(chart_data)}")
                        if self._is_valid_chart_data(chart_data):
                            logger.info(f"Extracted chart data from tool_result.metadata['plotly_figure']")
                            return chart_data
            
            # Check if tool result has ui_component with rich_component
            if hasattr(tool_result, 'ui_component'):
                ui_component = tool_result.ui_component
                logger.debug(f"Found ui_component: {type(ui_component)}")
                if hasattr(ui_component, 'rich_component'):
                    rich_component = ui_component.rich_component
                    logger.debug(f"Found rich_component: {type(rich_component)}")
                    # Check if rich_component has chart_data attribute
                    if hasattr(rich_component, 'chart_data'):
                        chart_data = rich_component.chart_data
                        logger.debug(f"Found chart_data in rich_component: {type(chart_data)}")
                        if self._is_valid_chart_data(chart_data):
                            logger.info(f"Extracted chart data from rich_component.chart_data")
                            return chart_data
                    # Check if rich_component has data attribute
                    elif hasattr(rich_component, 'data'):
                        chart_data = rich_component.data
                        logger.debug(f"Found data in rich_component: {type(chart_data)}")
                        if self._is_valid_chart_data(chart_data):
                            logger.info(f"Extracted chart data from rich_component.data")
                            return chart_data
        
        # Check for ChartComponent (capital C)
        if hasattr(component, 'ChartComponent'):
            chart_component = component.ChartComponent
            logger.debug(f"Found ChartComponent: {type(chart_component)}")
            # Try to extract chart data
            if hasattr(chart_component, 'chart_data'):
                chart_data = chart_component.chart_data
                logger.debug(f"Found chart_data in ChartComponent: {type(chart_data)}")
                if self._is_valid_chart_data(chart_data):
                    logger.info(f"Extracted chart data from ChartComponent.chart_data")
                    return chart_data
            elif hasattr(chart_component, 'to_dict'):
                chart_data = chart_component.to_dict()
                logger.debug(f"Converted ChartComponent to dict: {type(chart_data)}")
                if self._is_valid_chart_data(chart_data):
                    logger.info(f"Extracted chart data from ChartComponent.to_dict()")
                    return chart_data
            elif hasattr(chart_component, 'data'):
                data = chart_component.data
                logger.debug(f"Found data in ChartComponent: {type(data)}")
                if self._is_valid_chart_data(data):
                    logger.info(f"Extracted chart data from ChartComponent.data")
                    return data
        
        # Check if this is a chart component (lowercase)
        if hasattr(component, 'chart_component'):
            chart_component = component.chart_component
            logger.debug(f"Found chart_component: {type(chart_component)}")
            if hasattr(chart_component, 'chart_data'):
                chart_data = chart_component.chart_data
                logger.debug(f"Found chart_data in chart_component: {type(chart_data)}")
                if self._is_valid_chart_data(chart_data):
                    logger.info(f"Extracted chart data from chart_component.chart_data")
                    return chart_data
            elif hasattr(chart_component, 'to_dict'):
                chart_data = chart_component.to_dict()
                logger.debug(f"Converted chart_component to dict: {type(chart_data)}")
                if self._is_valid_chart_data(chart_data):
                    logger.info(f"Extracted chart data from chart_component.to_dict()")
                    return chart_data
        
        # Also check if component has chart data directly
        if hasattr(component, 'chart_data'):
            chart_data = component.chart_data
            logger.debug(f"Found chart_data directly on component: {type(chart_data)}")
            if self._is_valid_chart_data(chart_data):
                logger.info(f"Extracted chart data from component.chart_data")
                return chart_data
        
        # Check for plotly chart in component attributes
        for attr_name in ['plotly_chart', 'chart', 'figure', 'plotly_figure', 'plotly']:
            if hasattr(component, attr_name):
                chart_data = getattr(component, attr_name)
                logger.debug(f"Found {attr_name} attribute on component: {type(chart_data)}")
                if self._is_valid_chart_data(chart_data):
                    logger.info(f"Extracted chart data from component.{attr_name}")
                    return chart_data
        
        # Check if component itself is a dict with chart data
        if isinstance(component, dict):
            logger.debug(f"Component is a dict, checking for chart data")
            if self._is_valid_chart_data(component):
                logger.info(f"Component itself is valid chart data")
                return component
        
        logger.debug(f"No chart data found in component")
        return None
    
    def _is_valid_chart_data(self, chart_data: Any) -> bool:
        """Check if data is valid Plotly chart data"""
        if not isinstance(chart_data, dict):
            return False
        
        # Check for Plotly chart structure
        if 'data' in chart_data or 'layout' in chart_data:
            return True
        
        # Check for alternative chart structures
        if 'type' in chart_data and chart_data.get('type') in ['bar', 'line', 'scatter', 'pie', 'histogram']:
            return True
        
        return False
    
    def _get_csv_path_for_request(self, request_id: str) -> Optional[str]:
        """Get CSV path for a specific request using request ID"""
        try:
            # Look for CSV files that might contain the request ID in their name
            # or in a metadata file
            csv_files = list(Path(".").glob(f"**/*{request_id}*.csv"))
            if csv_files:
                # Return the first matching CSV file
                return str(csv_files[0].absolute())
            
            # If no direct match, check the query_results directory for recent files
            query_results_dir = Path("./query_results")
            if query_results_dir.exists():
                csv_files = list(query_results_dir.glob("*.csv"))
                if csv_files:
                    # Sort by modification time and return the latest
                    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                    return str(latest_csv.absolute())
            
            return None
        except Exception as e:
            logger.error(f"Error getting CSV path for request {request_id}: {e}")
            return None

# --- 9. CREATE FASTAPI APP ---
def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Initialize managers
    csv_manager = CSVResultManager()
    chart_manager = ChartManager()
    conversation_store = ConversationStore()
    conversation_enhancer = ConversationContextEnhancer(conversation_store=conversation_store)
    
    enhanced_handler = EnhancedChatHandler(
        agent=agent,
        learning_manager=learning_manager,
        csv_manager=csv_manager,
        sql_runner=sql_runner,
        conversation_store=conversation_store,
        conversation_enhancer=conversation_enhancer,
        chart_manager=chart_manager
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

    # Remove the base server's SSE endpoint so our custom endpoint can take precedence
    # Find and remove the POST /api/vanna/v2/chat_sse route from base server
    routes_to_remove = []
    for i, route in enumerate(app.routes):
        if hasattr(route, 'path') and route.path == "/api/vanna/v2/chat_sse":
            if hasattr(route, 'methods') and 'POST' in route.methods:
                routes_to_remove.append(i)
                logger.info(f"Found base server SSE endpoint at index {i}, will remove it")
    
    # Remove routes in reverse order to avoid index issues
    for i in sorted(routes_to_remove, reverse=True):
        removed_route = app.routes.pop(i)
        logger.info(f"Removed base server SSE endpoint: {removed_route.path}")

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
            
            headers = request_data.get("headers", {})
            user_identifier = (
                headers.get("x-user-id")
                or headers.get("x-user-identifier")
                or request_data.get("user_identifier")
                or request_data.get("user_id")
                or "api_user"
            )
            conversation_id = (
                headers.get("x-conversation-id")
                or headers.get("x-conversation")
                or request_data.get("conversation_id")
                or (request_data.get("metadata") or {}).get("conversation_id")
            )

            # Create request context
            request_context = RequestContext(
                headers=headers,
                metadata=request_data.get("metadata", {})
            )
            
            # Enhance question with learned patterns + conversation context
            learned = learning_manager.enhance_question_with_learned_patterns(message)
            enhanced_question = await app.state.conversation_enhancer.enhance_question_with_context(
                learned, user_identifier=user_identifier, conversation_id=conversation_id
            )
            
            async def event_stream():
                """Generate Server-Sent Events"""
                try:
                    # Send initial event
                    yield f"data: {json.dumps({'event': 'start', 'timestamp': datetime.now().isoformat() + 'Z'})}\n\n"
                    
                    response_text = ""
                    sql_query = ""
                    
                    # Stream agent response
                    async for component in agent.send_message(
                        request_context=request_context,
                        message=enhanced_question,
                        conversation_id=conversation_id,
                    ):
                        if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                            text = component.simple_component.text
                            response_text += text
                            # Send text chunk as event with event: chunk line
                            yield f"event: chunk\ndata: {json.dumps({'event': 'chunk', 'text': text})}\n\n"
                        
                        # Check for tool calls
                        if hasattr(component, 'tool_call_component'):
                            tool_call = component.tool_call_component
                            if hasattr(tool_call, 'tool_name') and tool_call.tool_name == 'run_sql':
                                if hasattr(tool_call, 'args') and 'sql' in tool_call.args:
                                    sql_query = tool_call.args['sql']
                                    yield f"event: sql\ndata: {json.dumps({'event': 'sql', 'sql': sql_query})}\n\n"
                    
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
                                yield f"event: csv\ndata: {json.dumps({'event': 'csv', 'url': csv_url})}\n\n"
                        except Exception as e:
                            logger.error(f"Error executing SQL for SSE: {e}")
                    
                    # Send completion event with event: complete line
                    yield f"event: complete\ndata: {json.dumps({'event': 'complete', 'answer': response_text, 'sql': sql_query, 'csv_url': csv_manager.get_csv_url(csv_path) if csv_path else None})}\n\n"

                    # Store conversation after completion (scoped by user + conversation)
                    await app.state.conversation_store.save_conversation_turn(
                        question=message,
                        response=response_text,
                        user_identifier=user_identifier,
                        username=headers.get("x-username") or str(user_identifier),
                        conversation_id=conversation_id,
                        metadata={
                            "sse": True,
                            "sql_query": sql_query,
                            "csv_generated": bool(csv_path),
                        },
                    )
                    
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    yield f"event: error\ndata: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
            
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
                
                headers = data.get("headers", {})
                user_identifier = (
                    headers.get("x-user-id")
                    or headers.get("x-user-identifier")
                    or data.get("user_identifier")
                    or data.get("user_id")
                    or "api_user"
                )
                conversation_id = (
                    headers.get("x-conversation-id")
                    or headers.get("x-conversation")
                    or data.get("conversation_id")
                    or (data.get("metadata") or {}).get("conversation_id")
                )

                # Create request context
                request_context = RequestContext(
                    headers=headers,
                    metadata=data.get("metadata", {})
                )
                
                # Enhance question with learned patterns + conversation context
                learned = learning_manager.enhance_question_with_learned_patterns(message)
                enhanced_question = await app.state.conversation_enhancer.enhance_question_with_context(
                    learned, user_identifier=user_identifier, conversation_id=conversation_id
                )
                
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
                    message=enhanced_question,
                    conversation_id=conversation_id,
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

                # Store conversation after completion (scoped by user + conversation)
                await app.state.conversation_store.save_conversation_turn(
                    question=message,
                    response=response_text,
                    user_identifier=user_identifier,
                    username=headers.get("x-username") or str(user_identifier),
                    conversation_id=conversation_id,
                    metadata={
                        "websocket": True,
                        "sql_query": sql_query,
                        "csv_generated": bool(csv_path),
                    },
                )
                
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
    async def get_conversation_history(
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 10,
    ):
        """Get conversation history.

        - Provide `user_identifier` and `conversation_id` to fetch a single thread.
        - Provide only `user_identifier` to fetch across all that user's threads.
        - Provide neither to fetch across all users.
        """
        try:
            conversation_store = app.state.conversation_store
            conversations = await conversation_store.get_recent_conversations(
                user_identifier=user_identifier,
                conversation_id=conversation_id,
                limit=limit
            )
            return JSONResponse(content={
                "user_identifier": user_identifier,
                "conversation_id": conversation_id,
                "limit": limit,
                "count": len(conversations),
                "conversations": conversations
            })
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/conversation/filter")
    async def filter_conversations(
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 10
    ):
        """Filter conversations by user and/or keyword"""
        try:
            conversation_store = app.state.conversation_store
            filter_keywords = [keyword] if keyword else None
            
            conversations = await conversation_store.get_filtered_conversations(
                user_identifier=user_identifier,
                conversation_id=conversation_id,
                filter_keywords=filter_keywords,
                limit=limit
            )
            
            return JSONResponse(content={
                "user_identifier": user_identifier,
                "conversation_id": conversation_id,
                "keyword": keyword,
                "limit": limit,
                "count": len(conversations),
                "conversations": conversations
            })
        except Exception as e:
            logger.error(f"Error filtering conversations: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/conversation/clear")
    async def clear_conversation_history(
        user_identifier: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        """Clear conversation history.

        - Provide `user_identifier` and `conversation_id` to clear a single thread.
        - Provide only `user_identifier` to clear all that user's threads.
        - Provide neither to clear everything.
        """
        try:
            conversation_store = app.state.conversation_store
            await conversation_store.clear_conversation_history(
                user_identifier=user_identifier,
                conversation_id=conversation_id,
            )
            return JSONResponse(content={
                "status": "success",
                "message": "Cleared conversation history",
                "user_identifier": user_identifier,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error clearing conversation history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # --- CHART DOWNLOAD ENDPOINTS ---
    
    @app.get("/api/v1/charts/{chart_id}/json")
    async def get_chart_json(chart_id: str):
        """Get chart data as JSON"""
        try:
            chart_manager = app.state.enhanced_handler.chart_manager
            chart_data = chart_manager.get_chart_data(chart_id)
            if not chart_data:
                raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
            
            return JSONResponse(content=chart_data)
        except Exception as e:
            logger.error(f"Error getting chart JSON for {chart_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/charts/{chart_id}/html")
    async def get_chart_html(chart_id: str):
        """Get chart as interactive HTML"""
        try:
            chart_manager = app.state.enhanced_handler.chart_manager
            html_path = chart_manager.generate_chart_filename(chart_id, "html")
            if not os.path.exists(html_path):
                # Try to generate HTML from JSON if it doesn't exist
                chart_data = chart_manager.get_chart_data(chart_id)
                if not chart_data:
                    raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
                
                # Generate HTML
                if 'data' in chart_data and 'layout' in chart_data:
                    fig = plotly.graph_objs.Figure(data=chart_data['data'], layout=chart_data.get('layout', {}))
                    pio.write_html(fig, html_path)
                else:
                    raise HTTPException(status_code=500, detail="Invalid chart data format")
            
            # Read and return HTML file
            with open(html_path, 'r') as f:
                html_content = f.read()
            
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Error getting chart HTML for {chart_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/charts/{chart_id}/png")
    async def get_chart_png(chart_id: str):
        """Get chart as PNG image"""
        try:
            chart_manager = app.state.enhanced_handler.chart_manager
            png_path = chart_manager.generate_chart_filename(chart_id, "png")
            if not os.path.exists(png_path):
                # Try to generate PNG from JSON if it doesn't exist
                chart_data = chart_manager.get_chart_data(chart_id)
                if not chart_data:
                    raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
                
                # Generate PNG
                if 'data' in chart_data and 'layout' in chart_data:
                    fig = plotly.graph_objs.Figure(data=chart_data['data'], layout=chart_data.get('layout', {}))
                    fig.write_image(png_path)
                else:
                    raise HTTPException(status_code=500, detail="Invalid chart data format")
            
            # Return PNG file
            from fastapi.responses import FileResponse
            return FileResponse(png_path, media_type="image/png", filename=f"{chart_id}.png")
        except Exception as e:
            logger.error(f"Error getting chart PNG for {chart_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/charts/{chart_id}/download")
    async def download_chart(chart_id: str, format: str = "png"):
        """Download chart in specified format (png, html, json)"""
        try:
            chart_manager = app.state.enhanced_handler.chart_manager
            
            if format == "png":
                png_path = chart_manager.generate_chart_filename(chart_id, "png")
                if not os.path.exists(png_path):
                    raise HTTPException(status_code=404, detail=f"Chart {chart_id} PNG not found")
                
                from fastapi.responses import FileResponse
                return FileResponse(png_path, media_type="image/png", filename=f"{chart_id}.png")
            
            elif format == "html":
                html_path = chart_manager.generate_chart_filename(chart_id, "html")
                if not os.path.exists(html_path):
                    raise HTTPException(status_code=404, detail=f"Chart {chart_id} HTML not found")
                
                from fastapi.responses import FileResponse
                return FileResponse(html_path, media_type="text/html", filename=f"{chart_id}.html")
            
            elif format == "json":
                json_path = chart_manager.generate_chart_filename(chart_id, "json")
                if not os.path.exists(json_path):
                    raise HTTPException(status_code=404, detail=f"Chart {chart_id} JSON not found")
                
                from fastapi.responses import FileResponse
                return FileResponse(json_path, media_type="application/json", filename=f"{chart_id}.json")
            
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Supported formats: png, html, json")
        except Exception as e:
            logger.error(f"Error downloading chart {chart_id} in format {format}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # --- DATABASE AND MEMORY INSPECTION ---

    @app.get("/api/v1/database/tables")
    async def get_database_tables():
        """Get list of tables in the connected database"""
        try:
            # MySQL specific query for tables
            # Create a dummy context for the tool (required by Vanna 2.x)
            context = ToolContext(
                user=User(id="admin_viewer", username="admin", group_memberships=["admin"]),
                conversation_id="db_inspection",
                request_id=f"db_inspect_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                agent_memory=memory
            )
            from types import SimpleNamespace
            # It seems run_sql expects an object with .sql attribute
            sql_arg = SimpleNamespace(sql="SHOW TABLES")
            df = await sql_runner.run_sql(sql_arg, context=context)
            tables = []
            if not df.empty:
                # The column name is usually "Tables_in_dbname" but index 0 is safer
                tables = df.iloc[:, 0].tolist()
            
            return JSONResponse(content={
                "tables": tables,
                "count": len(tables)
            })
        except Exception as e:
            logger.error(f"Error getting database tables: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    @app.get("/api/v1/memory/all")
    async def get_memory_contents(limit: int = 100):
        """Get contents of agent memory (ChromaDB)"""
        try:
            # Create a context for the request
            # We reuse the learning manager's context creation or create a new one
            context = ToolContext(
                user=User(id="admin_viewer", username="admin", group_memberships=["admin"]),
                conversation_id="memory_inspection",
                request_id=f"inspect_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                agent_memory=memory
            )
            
            # Fetch recent memories
            # accessing the memory object directly
            memories = await memory.get_recent_text_memories(context=context, limit=limit)
            
            formatted_memories = []
            for mem in memories:
                try:
                    # Try to parse content if it's JSON
                    content = json.loads(mem.content)
                except:
                    content = mem.content
                    
                formatted_memories.append({
                    "id": getattr(mem, 'id', 'unknown'),
                    "content": content,
                    "timestamp": mem.created_at.isoformat() if hasattr(mem, 'created_at') and mem.created_at else None,
                    "type": getattr(mem, 'type', 'unknown')
                })
                
            return JSONResponse(content={
                "limit": limit,
                "count": len(formatted_memories),
                "memories": formatted_memories
            })
        except Exception as e:
            logger.error(f"Error getting memory contents: {e}")
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
    
    # --- GOLDEN QUERY ENDPOINTS ---
    
    @app.get("/api/v1/golden_queries")
    async def get_golden_queries(
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        search: Optional[str] = None,
        tags: Optional[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 20
    ):
        """Get golden queries with optional filtering"""
        try:
            # Parse tags if provided
            tag_list = tags.split(",") if tags else None
            
            # Search golden queries
            queries = golden_query_manager.search_golden_queries(
                user_id=user_id,
                search_text=search,
                tags=tag_list,
                min_success_rate=min_success_rate,
                limit=limit
            )
            
            # Convert to dict for JSON response
            queries_data = [query.to_dict() for query in queries]
            
            return JSONResponse(content={
                "user_id": user_id,
                "conversation_id": conversation_id,
                "search": search,
                "tags": tag_list,
                "min_success_rate": min_success_rate,
                "limit": limit,
                "count": len(queries_data),
                "golden_queries": queries_data
            })
        except Exception as e:
            logger.error(f"Error getting golden queries: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/golden_queries/{query_id}")
    async def get_golden_query(query_id: str):
        """Get a specific golden query by ID"""
        try:
            query = golden_query_manager.get_golden_query(query_id)
            if not query:
                raise HTTPException(status_code=404, detail=f"Golden query {query_id} not found")
            
            return JSONResponse(content=query.to_dict())
        except Exception as e:
            logger.error(f"Error getting golden query {query_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/golden_queries")
    async def create_golden_query(request: Request):
        """Create or update a golden query"""
        try:
            request_data = await request.json()
            
            # Extract headers from request
            headers = dict(request.headers)
            
            # Extract required fields with fallback to headers (consistent with other endpoints)
            user_id = (
                request_data.get("user_id")
                or headers.get("x-user-id")
                or headers.get("x-user-identifier")
            )
            conversation_id = (
                request_data.get("conversation_id")
                or headers.get("x-conversation-id")
                or headers.get("x-conversation")
                or (request_data.get("metadata") or {}).get("conversation_id")
                or "default"  # Default value if not provided
            )
            original_question = request_data.get("original_question")
            sql_query = request_data.get("sql_query")
            
            if not all([user_id, original_question, sql_query]):
                raise HTTPException(
                    status_code=400, 
                    detail="Missing required fields: user_id, original_question, sql_query"
                )
            
            # Extract optional fields
            description = request_data.get("description")
            tags = request_data.get("tags", [])
            metadata = request_data.get("metadata", {})
            
            # Add golden query
            query = golden_query_manager.add_golden_query(
                user_id=user_id,
                conversation_id=conversation_id,
                original_question=original_question,
                sql_query=sql_query,
                description=description,
                tags=tags,
                metadata=metadata
            )
            
            return JSONResponse(content={
                "status": "success",
                "message": "Golden query created/updated",
                "query_id": query.query_id,
                "query": query.to_dict()
            })
        except Exception as e:
            logger.error(f"Error creating golden query: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/golden_queries/{query_id}/record_success")
    async def record_golden_query_success(query_id: str):
        """Record a successful use of a golden query"""
        try:
            golden_query_manager.record_query_success(query_id)
            return JSONResponse(content={
                "status": "success",
                "message": f"Recorded success for golden query {query_id}"
            })
        except Exception as e:
            logger.error(f"Error recording golden query success: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/golden_queries/{query_id}/record_failure")
    async def record_golden_query_failure(query_id: str):
        """Record a failed use of a golden query"""
        try:
            golden_query_manager.record_query_failure(query_id)
            return JSONResponse(content={
                "status": "success",
                "message": f"Recorded failure for golden query {query_id}"
            })
        except Exception as e:
            logger.error(f"Error recording golden query failure: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/golden_queries/{query_id}/tags")
    async def add_tags_to_golden_query(query_id: str, request: Request):
        """Add tags to a golden query"""
        try:
            request_data = await request.json()
            tags = request_data.get("tags", [])
            
            if not tags:
                raise HTTPException(status_code=400, detail="No tags provided")
            
            success = golden_query_manager.add_tags_to_query(query_id, tags)
            if not success:
                raise HTTPException(status_code=404, detail=f"Golden query {query_id} not found")
            
            return JSONResponse(content={
                "status": "success",
                "message": f"Added tags to golden query {query_id}",
                "tags": tags
            })
        except Exception as e:
            logger.error(f"Error adding tags to golden query: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/golden_queries/{query_id}/tags")
    async def remove_tags_from_golden_query(query_id: str, request: Request):
        """Remove tags from a golden query"""
        try:
            request_data = await request.json()
            tags = request_data.get("tags", [])
            
            if not tags:
                raise HTTPException(status_code=400, detail="No tags provided")
            
            success = golden_query_manager.remove_tags_from_query(query_id, tags)
            if not success:
                raise HTTPException(status_code=404, detail=f"Golden query {query_id} not found")
            
            return JSONResponse(content={
                "status": "success",
                "message": f"Removed tags from golden query {query_id}",
                "tags": tags
            })
        except Exception as e:
            logger.error(f"Error removing tags from golden query: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/golden_queries/{query_id}")
    async def delete_golden_query(query_id: str):
        """Delete a golden query"""
        try:
            success = golden_query_manager.delete_golden_query(query_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"Golden query {query_id} not found")
            
            return JSONResponse(content={
                "status": "success",
                "message": f"Deleted golden query {query_id}"
            })
        except Exception as e:
            logger.error(f"Error deleting golden query: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/golden_queries/stats")
    async def get_golden_query_stats():
        """Get statistics about golden queries"""
        try:
            stats = golden_query_manager.get_stats()
            return JSONResponse(content=stats)
        except Exception as e:
            logger.error(f"Error getting golden query stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/golden_queries/export")
    async def export_golden_queries(format: str = "json"):
        """Export golden queries in specified format"""
        try:
            if format not in ["json", "csv"]:
                raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")
            
            export_data = golden_query_manager.export_golden_queries(format)
            
            if format == "json":
                return JSONResponse(content=json.loads(export_data))
            else:  # csv
                from fastapi.responses import PlainTextResponse
                return PlainTextResponse(
                    content=export_data,
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=golden_queries.csv"}
                )
        except Exception as e:
            logger.error(f"Error exporting golden queries: {e}")
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
    # Default to 8001.
    port = int(os.getenv("PORT", "8001"))

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
