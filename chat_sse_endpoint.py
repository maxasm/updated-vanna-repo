"""
Production-ready FastAPI SSE endpoint for chat streaming.

This module implements the /api/vanna/v2/chat_sse endpoint with exactly the same
behavior and event structure as the original implementation.

Event flow:
1. event: start     → {event: "start", timestamp: isoformat}
2. event: chunk     → multiple times, each with partial text
3. event: sql       → once, when SQL is detected (if any)
4. event: csv       → once, when a result CSV file is detected/generated
5. event: complete  → final event with full answer + sql + csv_url (if any)
6. event: error     → only on fatal failure
"""

import os
import json
import re
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

# Configure logging
logger = logging.getLogger("chat_sse")


class SSEChatEndpoint:
    """
    Handles Server-Sent Events (SSE) streaming for chat interactions.
    
    This class encapsulates all the logic needed to:
    - Stream text chunks from an agent
    - Detect and extract SQL queries
    - Find generated CSV files
    - Send properly formatted SSE events
    """
    
    def __init__(
        self,
        agent,
        sql_runner,
        csv_manager,
        conversation_store=None,
        conversation_enhancer=None,
        learning_manager=None
    ):
        """
        Initialize the SSE chat endpoint.
        
        Args:
            agent: The Vanna agent instance for message processing
            sql_runner: MySQL runner for executing SQL queries
            csv_manager: Manager for CSV file operations
            conversation_store: Optional conversation history store
            conversation_enhancer: Optional conversation context enhancer
            learning_manager: Optional learning manager for pattern enhancement
        """
        self.agent = agent
        self.sql_runner = sql_runner
        self.csv_manager = csv_manager
        self.conversation_store = conversation_store
        self.conversation_enhancer = conversation_enhancer
        self.learning_manager = learning_manager
    
    async def handle_sse_request(self, request: Request) -> StreamingResponse:
        """
        Main handler for SSE chat requests.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            StreamingResponse with text/event-stream media type
            
        Raises:
            HTTPException: If request validation fails
        """
        try:
            # Parse request body
            data = await request.json()
            message = data.get("message", "")
            
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            # Extract headers and user information
            headers = data.get("headers", {})
            user_id = (
                headers.get("x-user-id")
                or headers.get("x-user-identifier")
                or data.get("user_id")
                or data.get("user_identifier")
                or "anonymous"
            )
            conversation_id = (
                headers.get("x-conversation-id")
                or headers.get("x-conversation")
                or data.get("conversation_id")
                or (data.get("metadata") or {}).get("conversation_id")
            )
            username = headers.get("x-username") or str(user_id)
            
            logger.info(
                f"SSE request from user={user_id}, conversation={conversation_id}, "
                f"message_length={len(message)}"
            )
            
            # Enhance question with learned patterns and conversation context
            enhanced_question = await self._enhance_question(
                message, user_id, conversation_id
            )
            
            # Create request context for agent
            from vanna.core.user import RequestContext
            request_context = RequestContext(
                headers=headers,
                metadata=data.get("metadata", {})
            )
            
            # Create and return streaming response
            return StreamingResponse(
                self._event_stream(
                    message=message,
                    enhanced_question=enhanced_question,
                    request_context=request_context,
                    user_id=user_id,
                    username=username,
                    conversation_id=conversation_id,
                    headers=headers
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable buffering for nginx
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("SSE endpoint failed")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _enhance_question(
        self,
        message: str,
        user_id: str,
        conversation_id: Optional[str]
    ) -> str:
        """
        Enhance the question with learned patterns and conversation context.
        
        Args:
            message: Original user message
            user_id: User identifier
            conversation_id: Conversation identifier
            
        Returns:
            Enhanced question string
        """
        enhanced = message
        
        # First enhance with learned patterns
        if self.learning_manager:
            try:
                enhanced = self.learning_manager.enhance_question_with_learned_patterns(
                    enhanced
                )
            except Exception as e:
                logger.warning(f"Error enhancing with learned patterns: {e}")
        
        # Then enhance with conversation context
        if self.conversation_enhancer:
            try:
                enhanced = await self.conversation_enhancer.enhance_question_with_context(
                    enhanced,
                    user_identifier=user_id,
                    conversation_id=conversation_id
                )
            except Exception as e:
                logger.warning(f"Error enhancing with conversation context: {e}")
        
        return enhanced
    
    async def _event_stream(
        self,
        message: str,
        enhanced_question: str,
        request_context,
        user_id: str,
        username: str,
        conversation_id: Optional[str],
        headers: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """
        Generate Server-Sent Events stream.
        
        This is the core streaming logic that:
        1. Sends start event
        2. Streams text chunks from agent
        3. Detects SQL queries and CSV files
        4. Sends sql and csv events
        5. Sends complete event
        6. Handles errors gracefully
        
        Args:
            message: Original user message
            enhanced_question: Enhanced question with context
            request_context: Vanna RequestContext
            user_id: User identifier
            username: Username
            conversation_id: Conversation identifier
            headers: Request headers
            
        Yields:
            SSE formatted event strings
        """
        try:
            # Send initial start event
            yield self._format_sse_event(
                event_type="start",
                data={"event": "start", "timestamp": datetime.now().isoformat()}
            )
            
            # Initialize tracking variables
            full_response = ""
            sql_query = ""
            captured_csv_filename = None
            csv_before = None
            
            # Track CSV before query (for time window detection)
            try:
                csv_before = self._find_latest_csv()
            except Exception as e:
                logger.debug(f"Error finding initial CSV: {e}")
            
            # Stream agent response
            component_count = 0
            max_components = 100  # Safety limit to prevent infinite loops
            
            try:
                # Get the async iterator from agent.send_message
                agent_stream = self.agent.send_message(
                    request_context=request_context,
                    message=enhanced_question,
                    conversation_id=conversation_id,
                )
                
                # Process components from agent
                async for component in agent_stream:
                    if component_count >= max_components:
                        logger.warning(f"Reached maximum component limit of {max_components}")
                        break
                    
                    component_count += 1
                    
                    # Extract and stream text chunks
                    if hasattr(component, 'simple_component') and hasattr(
                        component.simple_component, 'text'
                    ):
                        text = component.simple_component.text
                        full_response += text
                        
                        # Send chunk event
                        yield self._format_sse_event(
                            event_type="chunk",
                            data={"event": "chunk", "text": text}
                        )
                        
                        # Check for CSV filename in text output
                        csv_filename = self._extract_csv_filename_from_text(text)
                        if csv_filename and not captured_csv_filename:
                            captured_csv_filename = csv_filename
                            logger.info(
                                f"Captured CSV filename from agent text: {captured_csv_filename}"
                            )
                    
                    # Check for tool calls (especially run_sql)
                    if hasattr(component, 'tool_call_component'):
                        tool_call = component.tool_call_component
                        if hasattr(tool_call, 'tool_name') and tool_call.tool_name == 'run_sql':
                            if hasattr(tool_call, 'args') and 'sql' in tool_call.args:
                                sql_query = tool_call.args['sql']
                                # Send SQL event immediately when detected
                                yield self._format_sse_event(
                                    event_type="sql",
                                    data={"event": "sql", "sql": sql_query}
                                )
                                logger.info(f"Captured SQL from tool call: {sql_query[:100]}...")
                
                logger.info(f"Agent stream completed after {component_count} components")
                
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for agent response")
                yield self._format_sse_event(
                    event_type="error",
                    data={"event": "error", "error": "Agent response timeout"}
                )
                return
            except Exception as e:
                logger.error(f"Error in agent stream: {e}")
                yield self._format_sse_event(
                    event_type="error",
                    data={"event": "error", "error": f"Agent error: {str(e)}"}
                )
                return
            
            # After streaming complete, determine CSV path
            csv_path = await self._find_csv_file(
                captured_csv_filename, csv_before, sql_query
            )
            
            # If we still don't have SQL but have response text, try to extract it
            if not sql_query and full_response:
                try:
                    extracted_sql = self._extract_sql_from_response(full_response)
                    if extracted_sql:
                        sql_query = extracted_sql
                        logger.info(f"Extracted SQL from response text: {sql_query[:100]}...")
                except Exception as e:
                    logger.error(f"Error extracting SQL from response text: {e}")
            
            # Send CSV event if we have a CSV path
            if csv_path:
                csv_url = self.csv_manager.get_csv_url(csv_path)
                yield self._format_sse_event(
                    event_type="csv",
                    data={"event": "csv", "url": csv_url}
                )
            
            # Send completion event
            yield self._format_sse_event(
                event_type="complete",
                data={
                    "event": "complete",
                    "answer": full_response.strip(),
                    "sql": sql_query,
                    "csv_url": self.csv_manager.get_csv_url(csv_path) if csv_path else None
                }
            )
            
            # Store conversation after completion
            if self.conversation_store:
                try:
                    await self.conversation_store.save_conversation_turn(
                        question=message,
                        response=full_response,
                        user_identifier=user_id,
                        username=username,
                        conversation_id=conversation_id,
                        metadata={
                            "sse": True,
                            "sql_query": sql_query,
                            "csv_generated": bool(csv_path),
                        },
                    )
                except Exception as e:
                    logger.error(f"Error saving conversation: {e}")
            
        except Exception as e:
            logger.exception("Error in SSE stream")
            yield self._format_sse_event(
                event_type="error",
                data={"event": "error", "error": str(e)}
            )
    
    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Format a Server-Sent Event.
        
        Args:
            event_type: Type of event (start, chunk, sql, csv, complete, error)
            data: Event data dictionary
            
        Returns:
            Formatted SSE string with event type and data
        """
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def _extract_csv_filename_from_text(self, text: str) -> Optional[str]:
        """
        Extract CSV filename from agent text output.
        
        Looks for patterns like:
        - "Results saved to file: query_results_xxx.csv"
        - "Saved to file: query_results_xxx.csv"
        - Any mention of "query_results_*.csv"
        
        Args:
            text: Text to search for CSV filename
            
        Returns:
            CSV filename if found, None otherwise
        """
        # Look for explicit "saved to file" patterns
        csv_match = re.search(
            r'(?:Results saved to file:|Saved to file:|saved to file:)\s*([\w\-_]+\.csv)',
            text,
            re.IGNORECASE
        )
        if csv_match:
            return csv_match.group(1)
        
        # Look for any CSV file containing "query_results"
        csv_file_match = re.search(r'([\w\-_]+\.csv)', text)
        if csv_file_match and 'query_results' in csv_file_match.group(1):
            return csv_file_match.group(1)
        
        return None
    
    async def _find_csv_file(
        self,
        captured_csv_filename: Optional[str],
        csv_before: Optional[str],
        sql_query: str
    ) -> Optional[str]:
        """
        Find the CSV file generated by the query.
        
        Strategy:
        1. If we captured a CSV filename from agent text, try to find it
        2. Otherwise, look for the latest CSV file (within time window)
        3. If we have SQL but no CSV, execute SQL to generate CSV
        
        Args:
            captured_csv_filename: CSV filename captured from agent text
            csv_before: CSV file that existed before query
            sql_query: SQL query that was executed
            
        Returns:
            Absolute path to CSV file, or None if not found
        """
        csv_path = None
        
        # First, try to use the captured CSV filename from agent text output
        if captured_csv_filename:
            try:
                captured_csv_path = self._find_csv_by_filename(captured_csv_filename)
                if captured_csv_path:
                    csv_path = captured_csv_path
                    logger.info(
                        f"Using captured CSV filename: {captured_csv_filename} -> {csv_path}"
                    )
                else:
                    # If not found by exact filename, try query_results directory
                    query_results_dir = Path("./query_results")
                    if query_results_dir.exists():
                        potential_csv = query_results_dir / captured_csv_filename
                        if potential_csv.exists():
                            csv_path = str(potential_csv.absolute())
                            logger.info(
                                f"Found captured CSV in query_results directory: {csv_path}"
                            )
                        else:
                            logger.warning(
                                f"Captured CSV filename '{captured_csv_filename}' not found"
                            )
            except Exception as e:
                logger.error(f"Error finding CSV by filename: {e}")
        
        # If we don't have a CSV path from captured filename, fall back to latest file
        if not csv_path:
            try:
                csv_after = self._find_latest_csv(max_age_seconds=30)
                if csv_after and csv_after != csv_before:
                    csv_path = csv_after
                    logger.info(f"Using latest CSV file: {csv_path}")
            except Exception as e:
                logger.error(f"Error finding latest CSV: {e}")
        
        # If we have SQL but no CSV path, try to execute SQL to generate CSV
        if sql_query and not csv_path:
            try:
                df = self.sql_runner.run_sql(sql_query)
                if not df.empty:
                    import hashlib
                    query_hash = hashlib.md5(sql_query.encode()).hexdigest()
                    csv_path = self.csv_manager.save_query_results(df, query_hash)
                    logger.info(f"Generated CSV from SQL: {csv_path}")
            except Exception as e:
                logger.error(f"Error executing SQL to generate CSV: {e}")
        
        return csv_path
    
    def _find_latest_csv(self, max_age_seconds: int = 30) -> Optional[str]:
        """
        Find the latest CSV file in the results directory.
        
        Args:
            max_age_seconds: Only return CSV files modified within this time window
            
        Returns:
            Absolute path to latest CSV file, or None if not found
        """
        try:
            import time
            current_time = time.time()
            
            # Search for CSV files in current directory and subdirectories
            csv_files = list(Path(".").glob("**/*.csv"))
            if not csv_files:
                return None
            
            # Filter files by modification time (only recent files)
            recent_csv_files = []
            for csv_file in csv_files:
                try:
                    mtime = csv_file.stat().st_mtime
                    age_seconds = current_time - mtime
                    if age_seconds <= max_age_seconds:
                        recent_csv_files.append((csv_file, mtime))
                except Exception as e:
                    logger.debug(f"Error checking file {csv_file}: {e}")
                    continue
            
            if not recent_csv_files:
                return None
            
            # Get the most recently modified CSV file
            latest_csv, _ = max(recent_csv_files, key=lambda x: x[1])
            
            # Return absolute path
            return str(latest_csv.absolute())
        except Exception as e:
            logger.error(f"Error finding latest CSV: {e}")
            return None
    
    def _find_csv_by_filename(self, filename: str) -> Optional[str]:
        """
        Find a CSV file by filename (search recursively).
        
        Args:
            filename: CSV filename to search for
            
        Returns:
            Absolute path to CSV file, or None if not found
        """
        try:
            # Search for CSV files with the given filename in all subdirectories
            csv_files = list(Path(".").glob(f"**/{filename}"))
            if csv_files:
                # Return the first matching CSV file (should be unique)
                return str(csv_files[0].absolute())
            
            # If not found with exact match, try case-insensitive search
            for csv_file in Path(".").glob("**/*.csv"):
                if csv_file.name.lower() == filename.lower():
                    return str(csv_file.absolute())
            
            return None
        except Exception as e:
            logger.error(f"Error finding CSV by filename '{filename}': {e}")
            return None
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """
        Extract SQL query from agent response text.
        
        Tries multiple strategies:
        1. Look for SQL in code blocks (```sql ... ```)
        2. Look for common SQL patterns (SELECT, SHOW, DESCRIBE)
        3. Extract SQL starting with keywords
        
        Args:
            response_text: Agent response text
            
        Returns:
            Extracted SQL query, or empty string if not found
        """
        logger.debug(f"Attempting to extract SQL from response (length: {len(response_text)})")
        
        # First, try to find SQL in code blocks (most reliable)
        sql_match = re.search(r'```(?:sql|SQL)\s*(.*?)\s*```', response_text, re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
            logger.info(f"Extracted SQL from code block: {sql_query[:100]}...")
            return sql_query
        
        # Try to find SQL statements without code blocks
        sql_patterns = [
            # SHOW commands - stop at semicolon or end
            r'(SHOW\s+(?:TABLES|DATABASES|COLUMNS|INDEXES|CREATE\s+TABLE)[^;]*)(?:;|$)',
            # SELECT statements
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
                logger.info(f"Extracted SQL using pattern: {sql[:100]}...")
                return sql
        
        # Try to find any SQL-like statement that starts with common keywords
        sql_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH']
        for keyword in sql_keywords:
            pattern = rf'\b{keyword}\b'
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                start_idx = match.start()
                remaining = response_text[start_idx:]
                # Try to find a reasonable end point
                end_match = re.search(r'[;.]\s*\n|\n\n|$', remaining)
                if end_match:
                    end_idx = start_idx + end_match.start()
                    sql = response_text[start_idx:end_idx].strip()
                    # Basic validation: should contain SQL keywords
                    if len(sql.split()) > 2:  # At least 3 words
                        logger.info(f"Extracted SQL starting with '{keyword}': {sql[:100]}...")
                        return sql
        
        logger.debug("No SQL found in response text")
        return ""


def create_sse_endpoint(app: FastAPI, endpoint_handler: SSEChatEndpoint):
    """
    Register the SSE endpoint with a FastAPI app.
    
    Args:
        app: FastAPI application instance
        endpoint_handler: SSEChatEndpoint instance
    """
    @app.post("/api/vanna/v2/chat_sse")
    async def chat_sse_endpoint(request: Request):
        """
        POST /api/vanna/v2/chat_sse
        
        Server-Sent Events endpoint for streaming chat responses.
        
        Request body:
        {
            "message": str (required),
            "headers": {
                "x-user-id": str (optional),
                "x-conversation-id": str (optional),
                "x-username": str (optional)
            },
            "conversation_id": str (optional, fallback if not in headers),
            "user_id": str (optional, fallback if not in headers)
        }
        
        SSE Events:
        - event: start     → {event: "start", timestamp: isoformat}
        - event: chunk     → {event: "chunk", text: str} (multiple)
        - event: sql       → {event: "sql", sql: str} (if SQL detected)
        - event: csv       → {event: "csv", url: str} (if CSV generated)
        - event: complete  → {event: "complete", answer: str, sql: str, csv_url: str}
        - event: error     → {event: "error", error: str} (on failure)
        """
        return await endpoint_handler.handle_sse_request(request)
    
    logger.info("SSE endpoint registered at POST /api/vanna/v2/chat_sse")
