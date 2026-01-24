import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from vanna.core.tool.models import ToolContext
from vanna.integrations.chromadb import ChromaAgentMemory

logger = logging.getLogger(__name__)

@dataclass
class QueryPattern:
    """Represents a pattern extracted from a successful query"""
    pattern_id: str
    question_pattern: str
    sql_pattern: str
    tool_name: str
    success_count: int
    last_used: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryPattern':
        return cls(**data)

@dataclass  
class ToolUsagePattern:
    """Represents a pattern of tool usage"""
    pattern_id: str
    tool_name: str
    question_pattern: str
    args_pattern: Dict[str, Any]
    success_count: int
    failure_count: int
    last_used: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolUsagePattern':
        return cls(**data)

class LearningManager:
    """Manages learning from successful queries and tool usage patterns"""
    
    def __init__(self, agent_memory: ChromaAgentMemory):
        self.memory = agent_memory
        self.query_patterns: Dict[str, QueryPattern] = {}
        self.tool_patterns: Dict[str, ToolUsagePattern] = {}
        # Note: _load_patterns is async, so we need to call it properly
        # We'll load patterns on first use or in an async context
        self._patterns_loaded = False
    
    async def ensure_patterns_loaded(self):
        """Ensure patterns are loaded (call this before using patterns)"""
        if not self._patterns_loaded:
            await self._load_patterns()
            self._patterns_loaded = True
    
    def _create_tool_context(self) -> ToolContext:
        """Create a ToolContext for memory operations"""
        from vanna.core.user import User
        return ToolContext(
            user=User(id="admin_user", username="admin", group_memberships=["admin"]),
            conversation_id=f"learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request_id=f"learn_req_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            agent_memory=self.memory
        )
    
    async def _load_patterns(self):
        """Load existing patterns from memory"""
        try:
            context = self._create_tool_context()
            # Try to load query patterns
            recent_memories = await self.memory.get_recent_text_memories(context=context, limit=100)
            for memory_item in recent_memories:
                try:
                    data = json.loads(memory_item.content)
                    if data.get('type') == 'query_pattern':
                        pattern = QueryPattern.from_dict(data['pattern'])
                        self.query_patterns[pattern.pattern_id] = pattern
                    elif data.get('type') == 'tool_usage_pattern':
                        pattern = ToolUsagePattern.from_dict(data['pattern'])
                        self.tool_patterns[pattern.pattern_id] = pattern
                except (json.JSONDecodeError, KeyError):
                    continue
            logger.info(f"Loaded {len(self.query_patterns)} query patterns and {len(self.tool_patterns)} tool patterns")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
    
    def _save_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]):
        """Save a pattern to memory"""
        try:
            memory_content = json.dumps({
                "type": pattern_type,
                "pattern": pattern_data,
                "timestamp": datetime.now().isoformat()
            })
            context = self._create_tool_context()
            self.memory.save_text_memory(content=memory_content, context=context)
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
    
    def extract_sql_pattern(self, sql_query: str) -> str:
        """Extract a pattern from an SQL query by replacing specific values with placeholders"""
        if not sql_query:
            return ""
        
        # Remove comments
        sql = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Normalize whitespace
        sql = ' '.join(sql.split())
        
        # Replace specific values with placeholders
        # Replace string literals
        sql = re.sub(r"'[^']*'", "'STRING_LITERAL'", sql)
        # Replace numeric literals
        sql = re.sub(r'\b\d+\b', 'NUMERIC_LITERAL', sql)
        # Replace table names (simplified - could be more sophisticated)
        # This is a basic implementation
        sql = re.sub(r'\b(FROM|JOIN|INTO|UPDATE)\s+(\w+)', r'\1 TABLE_NAME', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\b(SELECT)\s+(\w+)', r'\1 COLUMN_NAME', sql, flags=re.IGNORECASE)
        
        return sql
    
    def extract_question_pattern(self, question: str) -> str:
        """Extract a pattern from a natural language question"""
        # Remove specific values and replace with placeholders
        # This is a simplified version - could use NLP for better pattern extraction
        question_lower = question.lower()
        
        # Replace numbers
        pattern = re.sub(r'\b\d+\b', 'NUMBER', question)
        # Replace specific table/column mentions (basic)
        pattern = re.sub(r'\b(customers|orders|products|employees|payments)\b', 'TABLE_NAME', pattern, flags=re.IGNORECASE)
        
        return pattern
    
    def record_tool_usage(self, question: str, tool_name: str, args: Dict[str, Any], 
                         success: bool, metadata: Optional[Dict[str, Any]] = None):
        """Record tool usage and extract patterns from successful usage"""
        try:
            context = self._create_tool_context()
            
            # Save to Vanna's built-in tool usage memory
            self.memory.save_tool_usage(
                question=question,
                tool_name=tool_name,
                args=args,
                context=context,
                success=success,
                metadata=metadata
            )
            
            # Extract and save patterns for successful tool usage
            if success:
                # Extract question pattern
                question_pattern = self.extract_question_pattern(question)
                
                # Create pattern ID
                pattern_id = f"{tool_name}_{hash(question_pattern) % 1000000:06d}"
                
                # Update or create tool usage pattern
                if pattern_id in self.tool_patterns:
                    pattern = self.tool_patterns[pattern_id]
                    pattern.success_count += 1
                    pattern.last_used = datetime.now().isoformat()
                else:
                    pattern = ToolUsagePattern(
                        pattern_id=pattern_id,
                        tool_name=tool_name,
                        question_pattern=question_pattern,
                        args_pattern=self._extract_args_pattern(args),
                        success_count=1,
                        failure_count=0,
                        last_used=datetime.now().isoformat(),
                        metadata=metadata or {}
                    )
                    self.tool_patterns[pattern_id] = pattern
                
                # Save pattern to memory
                self._save_pattern('tool_usage_pattern', pattern.to_dict())
                
                # If this is an SQL tool, also extract query pattern
                if tool_name == 'run_sql' and 'sql' in args:
                    sql_pattern = self.extract_sql_pattern(args['sql'])
                    query_pattern_id = f"sql_{hash(sql_pattern) % 1000000:06d}"
                    
                    if query_pattern_id in self.query_patterns:
                        qp = self.query_patterns[query_pattern_id]
                        qp.success_count += 1
                        qp.last_used = datetime.now().isoformat()
                    else:
                        qp = QueryPattern(
                            pattern_id=query_pattern_id,
                            question_pattern=question_pattern,
                            sql_pattern=sql_pattern,
                            tool_name=tool_name,
                            success_count=1,
                            last_used=datetime.now().isoformat(),
                            metadata={
                                'original_question': question,
                                'original_sql': args['sql'],
                                **({} if metadata is None else metadata)
                            }
                        )
                        self.query_patterns[query_pattern_id] = qp
                    
                    # Save query pattern to memory
                    self._save_pattern('query_pattern', qp.to_dict())
                    
                    logger.info(f"Saved query pattern: {query_pattern_id}")
                
                logger.info(f"Recorded successful tool usage: {tool_name}")
            
        except Exception as e:
            logger.error(f"Error recording tool usage: {e}")
    
    def _extract_args_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patterns from tool arguments"""
        args_pattern = {}
        for key, value in args.items():
            if isinstance(value, str):
                # For SQL queries, use the extracted pattern
                if key == 'sql':
                    args_pattern[key] = self.extract_sql_pattern(value)
                else:
                    # For other strings, replace specific values
                    args_pattern[key] = re.sub(r'\b\d+\b', 'NUMBER', value)
            elif isinstance(value, (int, float)):
                args_pattern[key] = 'NUMERIC_VALUE'
            elif isinstance(value, list):
                args_pattern[key] = ['LIST_VALUE' for _ in value]
            elif isinstance(value, dict):
                args_pattern[key] = {'DICT_VALUE': '...'}
            else:
                args_pattern[key] = str(type(value).__name__).upper()
        
        return args_pattern
    
    def find_similar_successful_queries(self, question: str, limit: int = 3) -> List[QueryPattern]:
        """Find similar successful queries for the given question"""
        try:
            question_pattern = self.extract_question_pattern(question)
            
            # Simple similarity based on pattern matching
            similar_patterns = []
            for pattern in self.query_patterns.values():
                # Calculate simple similarity (could be improved)
                similarity = self._calculate_pattern_similarity(question_pattern, pattern.question_pattern)
                if similarity > 0.5:  # Threshold
                    similar_patterns.append((similarity, pattern))
            
            # Sort by similarity and return top matches
            similar_patterns.sort(key=lambda x: x[0], reverse=True)
            return [pattern for _, pattern in similar_patterns[:limit]]
            
        except Exception as e:
            logger.error(f"Error finding similar queries: {e}")
            return []
    
    def find_similar_tool_usage(self, question: str, tool_name: Optional[str] = None, 
                               limit: int = 3) -> List[ToolUsagePattern]:
        """Find similar successful tool usage for the given question"""
        try:
            question_pattern = self.extract_question_pattern(question)
            
            # Use Vanna's built-in search for similar usage
            context = self._create_tool_context()
            similar_results = self.memory.search_similar_usage(
                question=question,
                context=context,
                limit=limit * 2,  # Get more to filter
                tool_name_filter=tool_name
            )
            
            # Filter to only successful usage and convert to our pattern format
            similar_patterns = []
            for result in similar_results:
                if result.success:
                    # Create a pattern from the result
                    pattern = ToolUsagePattern(
                        pattern_id=f"search_{hash(result.question) % 1000000:06d}",
                        tool_name=result.tool_name,
                        question_pattern=self.extract_question_pattern(result.question),
                        args_pattern=self._extract_args_pattern(result.args),
                        success_count=1,
                        failure_count=0,
                        last_used=datetime.now().isoformat(),
                        metadata=result.metadata or {}
                    )
                    similar_patterns.append(pattern)
            
            return similar_patterns[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar tool usage: {e}")
            return []
    
    def _calculate_pattern_similarity(self, pattern1: str, pattern2: str) -> float:
        """Calculate similarity between two patterns (simplified)"""
        # Convert to sets of words
        words1 = set(pattern1.lower().split())
        words2 = set(pattern2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def enhance_question_with_learned_patterns(self, question: str) -> str:
        """Enhance a question with learned patterns from successful queries"""
        try:
            # Find similar successful queries
            similar_queries = self.find_similar_successful_queries(question, limit=2)
            
            if not similar_queries:
                return question
            
            # Build enhancement
            enhancement_lines = ["\n=== Learned Patterns from Successful Queries ==="]
            
            for i, pattern in enumerate(similar_queries, 1):
                enhancement_lines.append(f"\nPattern {i} (Used {pattern.success_count} times successfully):")
                enhancement_lines.append(f"Question pattern: {pattern.question_pattern}")
                enhancement_lines.append(f"SQL pattern: {pattern.sql_pattern}")
                if pattern.metadata.get('original_question'):
                    enhancement_lines.append(f"Example: {pattern.metadata['original_question'][:100]}...")
            
            enhancement_lines.append("\n=== End Learned Patterns ===\n")
            
            enhancement = "\n".join(enhancement_lines)
            return f"{enhancement}\nOriginal question: {question}"
            
        except Exception as e:
            logger.error(f"Error enhancing question with learned patterns: {e}")
            return question
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about learning progress"""
        total_successful_queries = sum(p.success_count for p in self.query_patterns.values())
        total_tool_success = sum(p.success_count for p in self.tool_patterns.values())
        total_tool_failure = sum(p.failure_count for p in self.tool_patterns.values())
        
        return {
            "query_patterns_count": len(self.query_patterns),
            "tool_patterns_count": len(self.tool_patterns),
            "total_successful_queries": total_successful_queries,
            "total_tool_success": total_tool_success,
            "total_tool_failure": total_tool_failure,
            "success_rate": total_tool_success / (total_tool_success + total_tool_failure) 
                if (total_tool_success + total_tool_failure) > 0 else 0.0
        }
