import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class GoldenQuery:
    """Represents a golden (high-quality) query that can be reused as a template"""
    query_id: str
    user_id: str
    conversation_id: str
    original_question: str
    sql_query: str
    description: Optional[str] = None
    tags: List[str] = None
    success_count: int = 1
    failure_count: int = 0
    last_used: str = None
    created_at: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_used is None:
            self.last_used = datetime.now().isoformat()
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GoldenQuery':
        return cls(**data)
    
    def increment_success(self):
        """Increment success count and update last used timestamp"""
        self.success_count += 1
        self.last_used = datetime.now().isoformat()
    
    def increment_failure(self):
        """Increment failure count"""
        self.failure_count += 1
        self.last_used = datetime.now().isoformat()
    
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class GoldenQueryManager:
    """Manages golden (high-quality) queries for reuse and learning"""
    
    def __init__(self, storage_file: str = "golden_queries.json"):
        self.storage_file = Path(storage_file)
        self.golden_queries: Dict[str, GoldenQuery] = {}
        self._load_golden_queries()
    
    def _load_golden_queries(self):
        """Load golden queries from storage file"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    for query_id, query_data in data.items():
                        self.golden_queries[query_id] = GoldenQuery.from_dict(query_data)
                logger.info(f"Loaded {len(self.golden_queries)} golden queries from {self.storage_file}")
            else:
                logger.info(f"No golden queries file found at {self.storage_file}, starting fresh")
        except Exception as e:
            logger.error(f"Error loading golden queries: {e}")
            # Start with empty dict if loading fails
            self.golden_queries = {}
    
    def _save_golden_queries(self):
        """Save golden queries to storage file"""
        try:
            # Convert to dict
            data = {query_id: query.to_dict() for query_id, query in self.golden_queries.items()}
            
            # Ensure directory exists
            self.storage_file.parent.mkdir(exist_ok=True)
            
            # Save to file
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self.golden_queries)} golden queries to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving golden queries: {e}")
    
    def _generate_query_id(self, sql_query: str, user_id: str) -> str:
        """Generate a unique ID for a query based on SQL and user"""
        # Create a hash from SQL and user ID
        content = f"{sql_query}_{user_id}".encode('utf-8')
        return hashlib.md5(content).hexdigest()[:12]
    
    def add_golden_query(
        self,
        user_id: str,
        conversation_id: str,
        original_question: str,
        sql_query: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GoldenQuery:
        """Add a new golden query or update existing one"""
        query_id = self._generate_query_id(sql_query, user_id)
        
        if query_id in self.golden_queries:
            # Update existing query
            query = self.golden_queries[query_id]
            query.increment_success()
            if tags:
                # Add new tags, avoid duplicates
                for tag in tags:
                    if tag not in query.tags:
                        query.tags.append(tag)
            if metadata:
                query.metadata.update(metadata)
            logger.info(f"Updated existing golden query: {query_id}")
        else:
            # Create new golden query
            query = GoldenQuery(
                query_id=query_id,
                user_id=user_id,
                conversation_id=conversation_id,
                original_question=original_question,
                sql_query=sql_query,
                description=description,
                tags=tags or [],
                metadata=metadata or {},
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat()
            )
            self.golden_queries[query_id] = query
            logger.info(f"Added new golden query: {query_id}")
        
        # Save to disk
        self._save_golden_queries()
        
        return query
    
    def record_query_success(self, query_id: str):
        """Record a successful use of a golden query"""
        if query_id in self.golden_queries:
            self.golden_queries[query_id].increment_success()
            self._save_golden_queries()
            logger.debug(f"Recorded success for golden query: {query_id}")
    
    def record_query_failure(self, query_id: str):
        """Record a failed use of a golden query"""
        if query_id in self.golden_queries:
            self.golden_queries[query_id].increment_failure()
            self._save_golden_queries()
            logger.debug(f"Recorded failure for golden query: {query_id}")
    
    def get_golden_query(self, query_id: str) -> Optional[GoldenQuery]:
        """Get a golden query by ID"""
        return self.golden_queries.get(query_id)
    
    def get_user_golden_queries(self, user_id: str, limit: int = 50) -> List[GoldenQuery]:
        """Get golden queries for a specific user"""
        user_queries = [q for q in self.golden_queries.values() if q.user_id == user_id]
        # Sort by last used (most recent first)
        user_queries.sort(key=lambda x: x.last_used, reverse=True)
        return user_queries[:limit]
    
    def get_conversation_golden_queries(self, user_id: str, conversation_id: str, limit: int = 20) -> List[GoldenQuery]:
        """Get golden queries for a specific conversation"""
        conv_queries = [
            q for q in self.golden_queries.values() 
            if q.user_id == user_id and q.conversation_id == conversation_id
        ]
        # Sort by last used (most recent first)
        conv_queries.sort(key=lambda x: x.last_used, reverse=True)
        return conv_queries[:limit]
    
    def search_golden_queries(
        self,
        user_id: Optional[str] = None,
        search_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_success_rate: float = 0.0,
        limit: int = 20
    ) -> List[GoldenQuery]:
        """Search golden queries with various filters"""
        results = []
        
        for query in self.golden_queries.values():
            # Filter by user if specified
            if user_id and query.user_id != user_id:
                continue
            
            # Filter by success rate
            if query.success_rate() < min_success_rate:
                continue
            
            # Filter by tags if specified
            if tags and not any(tag in query.tags for tag in tags):
                continue
            
            # Filter by search text if specified
            if search_text:
                search_lower = search_text.lower()
                text_to_search = f"{query.original_question} {query.sql_query} {query.description or ''}".lower()
                if search_lower not in text_to_search:
                    continue
            
            results.append(query)
        
        # Sort by success rate (highest first), then by last used
        results.sort(key=lambda x: (-x.success_rate(), x.last_used), reverse=True)
        return results[:limit]
    
    def delete_golden_query(self, query_id: str) -> bool:
        """Delete a golden query by ID"""
        if query_id in self.golden_queries:
            del self.golden_queries[query_id]
            self._save_golden_queries()
            logger.info(f"Deleted golden query: {query_id}")
            return True
        return False
    
    def add_tags_to_query(self, query_id: str, tags: List[str]) -> bool:
        """Add tags to a golden query"""
        if query_id in self.golden_queries:
            query = self.golden_queries[query_id]
            for tag in tags:
                if tag not in query.tags:
                    query.tags.append(tag)
            self._save_golden_queries()
            logger.info(f"Added tags {tags} to golden query: {query_id}")
            return True
        return False
    
    def remove_tags_from_query(self, query_id: str, tags: List[str]) -> bool:
        """Remove tags from a golden query"""
        if query_id in self.golden_queries:
            query = self.golden_queries[query_id]
            query.tags = [tag for tag in query.tags if tag not in tags]
            self._save_golden_queries()
            logger.info(f"Removed tags {tags} from golden query: {query_id}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about golden queries"""
        total_queries = len(self.golden_queries)
        total_success = sum(q.success_count for q in self.golden_queries.values())
        total_failure = sum(q.failure_count for q in self.golden_queries.values())
        
        # Count by user
        users = {}
        for query in self.golden_queries.values():
            if query.user_id not in users:
                users[query.user_id] = 0
            users[query.user_id] += 1
        
        # Count by tag
        tags = {}
        for query in self.golden_queries.values():
            for tag in query.tags:
                if tag not in tags:
                    tags[tag] = 0
                tags[tag] += 1
        
        return {
            "total_golden_queries": total_queries,
            "total_successful_uses": total_success,
            "total_failed_uses": total_failure,
            "overall_success_rate": total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0.0,
            "unique_users": len(users),
            "users_with_most_queries": sorted(users.items(), key=lambda x: x[1], reverse=True)[:5],
            "most_common_tags": sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def export_golden_queries(self, format: str = "json") -> str:
        """Export golden queries in specified format"""
        if format == "json":
            data = {query_id: query.to_dict() for query_id, query in self.golden_queries.items()}
            return json.dumps(data, indent=2)
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "query_id", "user_id", "conversation_id", "original_question",
                "sql_query", "description", "tags", "success_count", "failure_count",
                "success_rate", "last_used", "created_at"
            ])
            
            # Write data
            for query in self.golden_queries.values():
                writer.writerow([
                    query.query_id,
                    query.user_id,
                    query.conversation_id,
                    query.original_question[:100],  # Truncate for CSV
                    query.sql_query[:200],  # Truncate for CSV
                    query.description[:100] if query.description else "",
                    ";".join(query.tags),
                    query.success_count,
                    query.failure_count,
                    f"{query.success_rate():.2f}",
                    query.last_used,
                    query.created_at
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Singleton instance for easy access
_golden_query_manager = None

def get_golden_query_manager(storage_file: str = "golden_queries.json") -> GoldenQueryManager:
    """Get or create the singleton GoldenQueryManager instance"""
    global _golden_query_manager
    if _golden_query_manager is None:
        _golden_query_manager = GoldenQueryManager(storage_file=storage_file)
    return _golden_query_manager