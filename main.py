import os
import logging
import asyncio
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate

# 1. Load environment variables immediately
load_dotenv()

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

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [VANNA AI APP] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# --- 2. USER RESOLVER (Required for 2.x) ---
class CLIUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="admin_user", username="admin", group_memberships=["admin"])

# --- 3. INITIALIZE SERVICES ---
api_key = os.getenv("OPENAI_API_KEY")
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

# --- 4. TOOL REGISTRY WITH LEARNING WRAPPER (Required for 2.x) ---
registry = ToolRegistry()

# FIX: Use 'sql_runner' as the argument name, not 'runner'
sql_tool = RunSqlTool(sql_runner=sql_runner)

# Create a wrapper to intercept tool usage for learning
class LearningToolWrapper:
    """Wraps a tool to intercept usage for learning"""
    
    def __init__(self, tool, learning_manager: LearningManager):
        self.tool = tool
        self.learning_manager = learning_manager
        self.tool_name = tool.__class__.__name__
    
    async def __call__(self, *args, **kwargs):
        # Extract question from context if available
        question = ""
        tool_context = None
        
        # Try to find question in kwargs or args
        for arg in args:
            if isinstance(arg, ToolContext):
                tool_context = arg
                # Question might be in metadata or we need to track it separately
                # For now, we'll track it at a higher level
                break
        
        # Call the original tool
        try:
            result = await self.tool(*args, **kwargs)
            
            # Determine success based on result
            success = True
            if isinstance(result, dict) and 'error' in result:
                success = False
            elif result is None:
                success = False
            
            # Record tool usage (we'll need to capture the actual question elsewhere)
            # This will be handled by the main loop
            
            return result
        except Exception as e:
            # Record failure
            # This will be handled by the main loop
            raise e

# Wrap the SQL tool for learning
wrapped_sql_tool = sql_tool  # We'll handle learning at a higher level for now

# Register tool with access groups matching our UserResolver
registry.register_local_tool(wrapped_sql_tool, access_groups=["admin"])

# --- 5. CHART GENERATOR ---
class ChartGenerator:
    """Generates charts from CSV files and saves them to disk"""
    
    def __init__(self, output_dir: str = "./charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_charts_from_csv(self, csv_path: str, max_charts: int = 3) -> List[str]:
        """Generate charts from a CSV file and return list of saved chart paths"""
        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                return []
            
            chart_paths = []
            csv_name = Path(csv_path).stem
            
            # Try to generate different types of charts based on data
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            # 1. Bar chart for categorical vs numeric data
            if categorical_cols and numeric_cols:
                for cat_col in categorical_cols[:2]:  # Try first 2 categorical columns
                    for num_col in numeric_cols[:2]:  # Try first 2 numeric columns
                        if len(chart_paths) >= max_charts:
                            break
                        
                        try:
                            # Group by categorical column and sum numeric column
                            if df[cat_col].nunique() <= 20:  # Limit to reasonable number of categories
                                chart_data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
                                
                                plt.figure(figsize=(10, 6))
                                chart_data.plot(kind='bar')
                                plt.title(f'{num_col} by {cat_col}')
                                plt.xlabel(cat_col)
                                plt.ylabel(num_col)
                                plt.xticks(rotation=45, ha='right')
                                plt.tight_layout()
                                
                                chart_name = f"{csv_name}_{cat_col}_{num_col}_bar.png"
                                chart_path = self.output_dir / chart_name
                                plt.savefig(chart_path, dpi=100)
                                plt.close()
                                
                                chart_paths.append(str(chart_path))
                        except Exception as e:
                            logging.debug(f"Failed to create bar chart: {e}")
                            continue
            
            # 2. Line chart for time series or sequential data
            if len(df) > 5 and numeric_cols:
                # Check if there's a column that looks like dates or sequence
                for i, col in enumerate(df.columns):
                    if any(date_term in col.lower() for date_term in ['date', 'time', 'year', 'month', 'day', 'timestamp']):
                        try:
                            # Try to convert to datetime
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                            if df[col].notna().any():
                                for num_col in numeric_cols[:2]:
                                    if len(chart_paths) >= max_charts:
                                        break
                                    
                                    plt.figure(figsize=(10, 6))
                                    plt.plot(df[col], df[num_col], marker='o')
                                    plt.title(f'{num_col} over {col}')
                                    plt.xlabel(col)
                                    plt.ylabel(num_col)
                                    plt.xticks(rotation=45, ha='right')
                                    plt.tight_layout()
                                    
                                    chart_name = f"{csv_name}_{col}_{num_col}_line.png"
                                    chart_path = self.output_dir / chart_name
                                    plt.savefig(chart_path, dpi=100)
                                    plt.close()
                                    
                                    chart_paths.append(str(chart_path))
                        except Exception as e:
                            logging.debug(f"Failed to create line chart: {e}")
                            continue
            
            # 3. Pie chart for categorical distribution
            if categorical_cols and numeric_cols:
                for cat_col in categorical_cols[:1]:
                    for num_col in numeric_cols[:1]:
                        if len(chart_paths) >= max_charts:
                            break
                        
                        try:
                            if df[cat_col].nunique() <= 10:  # Limit for pie chart
                                chart_data = df.groupby(cat_col)[num_col].sum()
                                
                                plt.figure(figsize=(8, 8))
                                plt.pie(chart_data.values, labels=chart_data.index, autopct='%1.1f%%')
                                plt.title(f'Distribution of {num_col} by {cat_col}')
                                
                                chart_name = f"{csv_name}_{cat_col}_{num_col}_pie.png"
                                chart_path = self.output_dir / chart_name
                                plt.savefig(chart_path, dpi=100)
                                plt.close()
                                
                                chart_paths.append(str(chart_path))
                        except Exception as e:
                            logging.debug(f"Failed to create pie chart: {e}")
                            continue
            
            # 4. Histogram for numeric data distribution
            if numeric_cols and len(chart_paths) < max_charts:
                for num_col in numeric_cols[:2]:
                    if len(chart_paths) >= max_charts:
                        break
                    
                    try:
                        plt.figure(figsize=(10, 6))
                        plt.hist(df[num_col].dropna(), bins=20, edgecolor='black')
                        plt.title(f'Distribution of {num_col}')
                        plt.xlabel(num_col)
                        plt.ylabel('Frequency')
                        plt.tight_layout()
                        
                        chart_name = f"{csv_name}_{num_col}_hist.png"
                        chart_path = self.output_dir / chart_name
                        plt.savefig(chart_path, dpi=100)
                        plt.close()
                        
                        chart_paths.append(str(chart_path))
                    except Exception as e:
                        logging.debug(f"Failed to create histogram: {e}")
                        continue
            
            return chart_paths
            
        except Exception as e:
            logging.error(f"Error generating charts from {csv_path}: {e}")
            return []
    
    def find_latest_csv(self, base_directory: str = ".") -> Optional[str]:
        """Find the latest CSV file in the directory or timestamped subdirectories"""
        try:
            base_path = Path(base_directory)
            csv_files = []
            
            # Look for CSV files in the base directory
            csv_files.extend(list(base_path.glob("*.csv")))
            
            # Look for CSV files in timestamped subdirectories (like 4a647de78d0d1b74)
            for subdir in base_path.iterdir():
                if subdir.is_dir() and subdir.name.isalnum() and len(subdir.name) >= 8:
                    # Check if it looks like a timestamped directory
                    csv_files.extend(list(subdir.glob("*.csv")))
            
            if not csv_files:
                return None
            
            # Get the most recently modified CSV file
            latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
            return str(latest_csv)
        except Exception as e:
            logging.error(f"Error finding latest CSV: {e}")
            return None

# --- 6. CONVERSATION STORE AND FILTERS ---
class ConversationStore:
    """Stores and manages conversation history"""
    
    def __init__(self, agent_memory: ChromaAgentMemory, max_history: int = 10):
        self.memory = agent_memory
        self.max_history = max_history
        self.conversation_id = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _create_tool_context(self) -> ToolContext:
        """Create a ToolContext for memory operations"""
        return ToolContext(
            user=User(id="admin_user", username="admin", group_memberships=["admin"]),
            conversation_id=self.conversation_id,
            request_id=f"req_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            agent_memory=self.memory
        )
    
    async def save_conversation_turn(self, question: str, response: str, metadata: Optional[Dict] = None):
        """Save a conversation turn (question + response) to memory"""
        if metadata is None:
            metadata = {}
        
        # Create conversation memory object with metadata embedded
        conversation_memory = {
            "conversation_id": self.conversation_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
            "type": "conversation",
            "metadata": metadata
        }
        
        # Save to memory - embed metadata in the content since save_text_memory doesn't accept metadata parameter
        memory_content = json.dumps(conversation_memory)
        context = self._create_tool_context()
        await self.memory.save_text_memory(
            content=memory_content,
            context=context
        )
    
    async def get_recent_conversations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        context = self._create_tool_context()
        recent_memories = await self.memory.get_recent_text_memories(context=context, limit=limit * 2)  # Get more to filter
        
        conversations = []
        for memory_item in recent_memories:
            try:
                # Parse the JSON content
                conversation_data = json.loads(memory_item.content)
                # Check if it's a conversation memory (has type field)
                if conversation_data.get('type') == 'conversation':
                    conversations.append(conversation_data)
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue
        
        # Return most recent conversations, up to limit
        return conversations[:limit]
    
    async def get_filtered_conversations(self, filter_keywords: List[str] = None, 
                                         filter_metadata: Dict[str, Any] = None,
                                         limit: int = 5) -> List[Dict[str, Any]]:
        """Get conversations filtered by keywords or metadata"""
        context = self._create_tool_context()
        recent_memories = await self.memory.get_recent_text_memories(context=context, limit=limit * 10)  # Get more to filter
        
        filtered_conversations = []
        for memory_item in recent_memories:
            try:
                conversation_data = json.loads(memory_item.content)
                # Check if it's a conversation memory
                if conversation_data.get('type') != 'conversation':
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
    
    async def clear_conversation_history(self):
        """Clear all conversation history (for testing/debugging)"""
        context = self._create_tool_context()
        recent_memories = await self.memory.get_recent_text_memories(context=context, limit=1000)
        for memory_item in recent_memories:
            try:
                conversation_data = json.loads(memory_item.content)
                if conversation_data.get('type') == 'conversation':
                    if hasattr(memory_item, 'memory_id'):
                        await self.memory.delete_by_id(memory_item.memory_id)
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

class ConversationContextEnhancer:
    """Enhances questions with conversation context"""
    
    def __init__(self, conversation_store: ConversationStore):
        self.store = conversation_store
    
    async def enhance_question_with_context(self, question: str) -> str:
        """Enhance the question with relevant conversation history"""
        # Get recent conversations
        recent_conversations = await self.store.get_recent_conversations(limit=3)
        
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

# --- 7. INITIALIZE AGENT AND CONVERSATION SYSTEM ---
agent = Agent(
    llm_service=llm,
    tool_registry=registry,
    user_resolver=CLIUserResolver(),
    agent_memory=memory,
    config=AgentConfig()
)

# Initialize conversation system
conversation_store = ConversationStore(agent_memory=memory)
conversation_enhancer = ConversationContextEnhancer(conversation_store=conversation_store)

# Initialize learning manager
learning_manager = LearningManager(agent_memory=memory)

# Initialize chart generator
chart_generator = ChartGenerator()

def initial_training():
    # Check if memory has get_training_data method (legacy Vanna 1.x)
    if hasattr(memory, 'get_training_data'):
        try:
            if not memory.get_training_data().empty:
                logger.info("Memory loaded.")
                return
        except Exception as e:
            logger.warning(f"Could not check training data: {e}")
    
    # Check if memory has train method (legacy Vanna 1.x)
    if hasattr(memory, 'train'):
        logger.warning("Training on schema...")
        try:
            df_schema = sql_runner.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS")
            for _, row in df_schema.iterrows():
                memory.train(documentation=f"Table {row['TABLE_NAME']} has column {row['COLUMN_NAME']}")
            logger.info("Training complete.")
        except Exception as e:
            logger.error(f"Training failed: {e}")
    else:
        logger.info("Skipping training (Vanna 2.x uses different training mechanism)")

async def run_cli():
    initial_training()
    print("\n" + "="*45 + "\n   VANNA AI AGENT V2.X ONLINE\n" + "="*45)
    print("   Conversation history enabled")
    print("   Chart generation enabled")
    print("   Learning over time enabled")
    print("="*45)
    
    # Load learning patterns
    await learning_manager.ensure_patterns_loaded()
    print(f"   Loaded {len(learning_manager.query_patterns)} query patterns")
    print(f"   Loaded {len(learning_manager.tool_patterns)} tool usage patterns")
    print("="*45)
    
    # Optional: Clear previous conversation history (uncomment if needed)
    # conversation_store.clear_conversation_history()
    # print("Cleared previous conversation history")
    
    while True:
        question = input("\n💬 Question: ").strip()
        if question.lower() in ['exit', 'quit']: break
        if not question: continue
        
        # Special commands for conversation management
        if question.lower() == '/history':
            print("\n📜 Conversation History:")
            conversations = await conversation_store.get_recent_conversations(limit=10)
            for i, conv in enumerate(conversations, 1):
                print(f"{i}. [{conv.get('timestamp', '')}]")
                print(f"   Q: {conv.get('question', '')}")
                print(f"   A: {conv.get('response', '')[:100]}..." if len(conv.get('response', '')) > 100 else f"   A: {conv.get('response', '')}")
                print()
            continue
        elif question.lower() == '/clear':
            await conversation_store.clear_conversation_history()
            print("🗑️  Conversation history cleared")
            continue
        elif question.lower() == '/charts':
            print("\n📊 Chart Generation:")
            latest_csv = chart_generator.find_latest_csv()
            if latest_csv:
                print(f"Found latest CSV: {latest_csv}")
                chart_paths = chart_generator.generate_charts_from_csv(latest_csv)
                if chart_paths:
                    print("Generated charts:")
                    for i, chart_path in enumerate(chart_paths, 1):
                        print(f"{i}. {chart_path}")
                else:
                    print("No charts could be generated from the CSV data.")
            else:
                print("No CSV files found.")
            continue
        elif question.lower().startswith('/filter '):
            keyword = question[8:].strip()
            if keyword:
                print(f"\n🔍 Conversations filtered by: '{keyword}'")
                filtered = await conversation_store.get_filtered_conversations(filter_keywords=[keyword], limit=10)
                for i, conv in enumerate(filtered, 1):
                    print(f"{i}. [{conv.get('timestamp', '')}]")
                    print(f"   Q: {conv.get('question', '')}")
                    print(f"   A: {conv.get('response', '')[:100]}..." if len(conv.get('response', '')) > 100 else f"   A: {conv.get('response', '')}")
                    print()
            continue
        elif question.lower() == '/learn':
            print("\n🧠 Learning Statistics:")
            stats = learning_manager.get_learning_stats()
            print(f"Query patterns stored: {stats['query_patterns_count']}")
            print(f"Tool usage patterns stored: {stats['tool_patterns_count']}")
            print(f"Total successful queries: {stats['total_successful_queries']}")
            print(f"Total tool successes: {stats['total_tool_success']}")
            print(f"Total tool failures: {stats['total_tool_failure']}")
            print(f"Success rate: {stats['success_rate']:.2%}")
            
            # Show some example patterns
            if stats['query_patterns_count'] > 0:
                print("\n📊 Example Query Patterns:")
                for i, (pattern_id, pattern) in enumerate(list(learning_manager.query_patterns.items())[:3], 1):
                    print(f"{i}. ID: {pattern_id}")
                    print(f"   Question pattern: {pattern.question_pattern[:50]}...")
                    print(f"   SQL pattern: {pattern.sql_pattern[:50]}...")
                    print(f"   Success count: {pattern.success_count}")
            
            if stats['tool_patterns_count'] > 0:
                print("\n🔧 Example Tool Usage Patterns:")
                for i, (pattern_id, pattern) in enumerate(list(learning_manager.tool_patterns.items())[:3], 1):
                    print(f"{i}. ID: {pattern_id}")
                    print(f"   Tool: {pattern.tool_name}")
                    print(f"   Question pattern: {pattern.question_pattern[:50]}...")
                    print(f"   Success count: {pattern.success_count}")
            continue
        elif question.lower() == '/learn_enhance':
            print("\n🤖 Testing Learning Enhancement:")
            test_question = input("Enter a test question: ").strip()
            if test_question:
                enhanced = learning_manager.enhance_question_with_learned_patterns(test_question)
                print("\nEnhanced question with learned patterns:")
                print(enhanced)
            continue

        try:
            # First enhance with learned patterns
            learned_enhanced_question = learning_manager.enhance_question_with_learned_patterns(question)
            
            # Then enhance with conversation context
            enhanced_question = await conversation_enhancer.enhance_question_with_context(learned_enhanced_question)
            
            # Create request context for CLI
            request_context = RequestContext()
            
            # Track if we had a successful query (CSV generated)
            csv_before = chart_generator.find_latest_csv()
            
            # send_message returns an async generator in Vanna 2.x
            response_text = ""
            response_data = None
            
            async for component in agent.send_message(request_context=request_context, message=enhanced_question):
                # In a real UI, we would handle different component types
                # For CLI, we just collect text responses
                if hasattr(component, 'simple_component') and hasattr(component.simple_component, 'text'):
                    response_text += component.simple_component.text + "\n"
                # We could also check for data in the component
            
            # Print text response
            if response_text:
                print(f"\n🤖 Agent: {response_text}")
                
                # Save conversation to history
                await conversation_store.save_conversation_turn(
                    question=question,
                    response=response_text,
                    metadata={
                        "enhanced_question": enhanced_question[:200] + "..." if len(enhanced_question) > 200 else enhanced_question,
                        "learned_enhanced": learned_enhanced_question[:200] + "..." if len(learned_enhanced_question) > 200 else learned_enhanced_question
                    }
                )
                
                # Check if a CSV was generated (indicating successful SQL execution)
                csv_after = chart_generator.find_latest_csv()
                query_success = False
                sql_query = ""
                
                # Try to extract SQL from response text
                import re
                sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
                if not sql_match:
                    # Try other SQL patterns
                    sql_match = re.search(r'SELECT .*?FROM', response_text, re.DOTALL | re.IGNORECASE)
                
                if sql_match:
                    sql_query = sql_match.group(1) if sql_match.group(1) else sql_match.group(0)
                    sql_query = sql_query.strip()
                    print(f"\n🔍 Extracted SQL from response: {sql_query[:100]}...")
                
                if csv_after and csv_after != csv_before:
                    # A new CSV was generated - this indicates successful SQL execution
                    query_success = True
                    print(f"\n✅ Query executed successfully, results saved to: {csv_after}")
                    
                    # Record tool usage with extracted SQL if available
                    sql_to_store = sql_query if sql_query else "EXTRACTED_FROM_AGENT"
                    learning_manager.record_tool_usage(
                        question=question,
                        tool_name="run_sql",
                        args={"sql": sql_to_store, "result_file": csv_after},
                        success=True,
                        metadata={
                            "csv_file": csv_after, 
                            "response_preview": response_text[:100],
                            "sql_extracted": bool(sql_query)
                        }
                    )
                
                # Check if we should generate charts automatically
                # Look for CSV files that might have been generated
                latest_csv = chart_generator.find_latest_csv()
                if latest_csv:
                    # Check if the response mentions data that could be visualized
                    chart_keywords = ['table', 'data', 'results', 'summary', 'analysis', 'chart', 'graph', 'visualize']
                    if any(keyword in response_text.lower() for keyword in chart_keywords):
                        print("\n📊 Generating charts from latest data...")
                        chart_paths = chart_generator.generate_charts_from_csv(latest_csv, max_charts=2)
                        if chart_paths:
                            print("Charts generated and saved:")
                            for chart_path in chart_paths:
                                print(f"  - {chart_path}")
                        else:
                            print("No suitable data for chart generation.")
            else:
                print("\n🤖 Agent: (No text response)")
                # Record failure if we got no response
                learning_manager.record_tool_usage(
                    question=question,
                    tool_name="agent_response",
                    args={},
                    success=False,
                    metadata={"error": "No response from agent"}
                )
            
            # Print data if present (simplified - would need actual data extraction)
            # if response_data is not None:
            #     print("\n" + tabulate(response_data, headers='keys', tablefmt='psql', showindex=False))
                
        except Exception as e:
            logger.error(f"Error: {e}")
            # Record failure
            learning_manager.record_tool_usage(
                question=question,
                tool_name="agent_execution",
                args={},
                success=False,
                metadata={"error": str(e)}
            )

if __name__ == "__main__":
    asyncio.run(run_cli())
