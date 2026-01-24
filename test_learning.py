#!/usr/bin/env python3
"""Test script for learning functionality"""

import asyncio
import json
from learning_manager import LearningManager, QueryPattern, ToolUsagePattern

async def test_learning_manager_basic():
    """Test basic LearningManager functionality without complex dependencies"""
    print("🧪 Testing LearningManager basic functionality...")
    
    # Create a simple mock that doesn't require complex validation
    class SimpleMockMemory:
        def __init__(self):
            self.saved_tool_usage = []
            self.saved_memories = []
        
        async def save_tool_usage(self, question, tool_name, args, context, success=True, metadata=None):
            self.saved_tool_usage.append({
                'question': question,
                'tool_name': tool_name,
                'success': success
            })
            print(f"  [Mock] Saved tool usage: {tool_name} - Success: {success}")
        
        async def save_text_memory(self, content, context):
            self.saved_memories.append(content)
            print(f"  [Mock] Saved text memory: {content[:50]}...")
        
        async def get_recent_text_memories(self, context, limit=10):
            return []
        
        async def search_similar_usage(self, question, context, limit=10, similarity_threshold=0.7, tool_name_filter=None):
            return []
    
    # Create learning manager with simple mock
    memory = SimpleMockMemory()
    
    # Create LearningManager instance manually
    learning_manager = LearningManager.__new__(LearningManager)
    learning_manager.memory = memory
    learning_manager.query_patterns = {}
    learning_manager.tool_patterns = {}
    learning_manager._patterns_loaded = True
    
    # Test pattern extraction
    print("\n📝 Testing pattern extraction...")
    
    sql_query = "SELECT * FROM customers WHERE country = 'USA' AND creditLimit > 10000"
    sql_pattern = learning_manager.extract_sql_pattern(sql_query)
    print(f"  Original SQL: {sql_query}")
    print(f"  Extracted pattern: {sql_pattern}")
    
    question = "Show me customers from USA with credit limit over 10000"
    question_pattern = learning_manager.extract_question_pattern(question)
    print(f"  Original question: {question}")
    print(f"  Extracted pattern: {question_pattern}")
    
    # Test args pattern extraction
    print("\n🔧 Testing args pattern extraction...")
    args = {"sql": sql_query, "limit": 10, "database": "classicmodels"}
    args_pattern = learning_manager._extract_args_pattern(args)
    print(f"  Original args: {args}")
    print(f"  Extracted args pattern: {args_pattern}")
    
    # Test pattern similarity
    print("\n📊 Testing pattern similarity...")
    pattern1 = "show customers from country with credit limit"
    pattern2 = "find customers in country with high credit"
    similarity = learning_manager._calculate_pattern_similarity(pattern1, pattern2)
    print(f"  Pattern 1: {pattern1}")
    print(f"  Pattern 2: {pattern2}")
    print(f"  Similarity: {similarity:.2f}")
    
    # Test creating patterns
    print("\n🎯 Testing pattern creation...")
    
    # Create a query pattern
    query_pattern = QueryPattern(
        pattern_id="test_001",
        question_pattern=question_pattern,
        sql_pattern=sql_pattern,
        tool_name="run_sql",
        success_count=1,
        last_used=datetime.now().isoformat(),
        metadata={"test": True}
    )
    
    print(f"  Created QueryPattern: {query_pattern.pattern_id}")
    print(f"  Question pattern: {query_pattern.question_pattern}")
    print(f"  SQL pattern: {query_pattern.sql_pattern}")
    
    # Test pattern serialization
    pattern_dict = query_pattern.to_dict()
    print(f"  Serialized to dict: {pattern_dict['pattern_id']}")
    
    # Test enhancing questions (without actual patterns)
    print("\n🤖 Testing question enhancement (no patterns yet)...")
    enhanced = learning_manager.enhance_question_with_learned_patterns(
        "Get orders from last month"
    )
    print(f"  Enhanced question (should be unchanged): {enhanced[:80]}...")
    
    # Add a pattern and test again
    learning_manager.query_patterns["test_001"] = query_pattern
    
    enhanced_with_pattern = learning_manager.enhance_question_with_learned_patterns(
        "Show customers from USA"
    )
    print(f"\n  Enhanced with pattern (preview): {enhanced_with_pattern[:120]}...")
    
    # Test learning stats
    print("\n📈 Testing learning statistics...")
    stats = learning_manager.get_learning_stats()
    print(f"  Query patterns: {stats['query_patterns_count']}")
    print(f"  Tool patterns: {stats['tool_patterns_count']}")
    print(f"  Total successful queries: {stats['total_successful_queries']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    
    print("\n✅ All basic tests completed!")

if __name__ == "__main__":
    # Import datetime here to avoid circular import
    from datetime import datetime
    asyncio.run(test_learning_manager_basic())
