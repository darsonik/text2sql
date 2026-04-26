"""Production-ready SQL query tool with input validation and sanitization.

This module provides enterprise-grade SQL query functionality with:
- Input validation and sanitization
- SQL injection protection
- Query length limits
- Error handling and logging
- Rate limiting preparation
"""

import re
import logging
import html
import uuid
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from langchain.tools import tool
from llama_index.core import SQLDatabase
from sqlalchemy import create_engine

from text2sql.models.llm_models import fireworks_embed_model, llama_index_llm
from text2sql.retrieval.llama_index_connector import LlamaIndexConnector

# Configure logging
logger = logging.getLogger(__name__)

# SQL injection patterns to detect and block
SQL_INJECTION_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script|declare|truncate)\b.*){2,}",
    r"(--|#|/\*|\*/)",
    r"(\b(or|and)\b.*=.*=)",
    r"(\bunion\b.*\bselect\b)",
    r"(\bdrop\b.*\btable\b)",
    r"(\bexec\b.*\b\()",
    r"(\bxp_cmdshell\b)",
    r"(\bsp_executesql\b)",
    r"(\'|\")\s*(or|and)\s*(\'|\")\s*=",
    r"\'\s*(or|and)\s*\'\s*=",
    r"\'\s*or\s*\'.*=.*\'\s*=",
    r"\'.*or.*\'.*=.*\'.*=",
    r"\'.*=.*\'.*or.*\'.*=",
    r"or\s*\'.*\'.*=.*\'.*=",
    r"\'.*or.*\'.*=.*\'.*=.*\'.*=",
    r"\b1\s*=\s*1\b"
]

# Query validation limits
MAX_QUERY_LENGTH = 1000
MIN_QUERY_LENGTH = 3
ALLOWED_SPECIAL_CHARS = r'[\w\s.,!?;:\-\'"()]+'

# Production database configuration
PRODUCTION_DB_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/production.db"
PRODUCTION_TABLES = [
    "organizations", "users", "categories", "products", 
    "orders", "order_items", "payments", "audit_logs"
]

# Database connection settings
DB_CONNECTION_TIMEOUT = 30  # seconds
DB_CONNECTION_RETRY_ATTEMPTS = 3
DB_CONNECTION_POOL_SIZE = 10
DB_CONNECTION_MAX_OVERFLOW = 20

# Create production database engine
def get_production_engine():
    """Create SQLAlchemy engine for production database with connection pooling."""
    try:
        # Check if database file exists, if not initialize it
        if not Path(PRODUCTION_DB_PATH).exists():
            logger.warning(f"Production database not found at {PRODUCTION_DB_PATH}. Please run initialize_db_native.py first.")
            # Try to initialize it
            try:
                from text2sql.database.initialize_db_native import initialize_native
                initialize_native()
                logger.info("Production database initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize production database: {e}")
                raise RuntimeError(f"Production database not available: {e}")
        
        # Create SQLAlchemy engine with connection pooling for production
        engine = create_engine(
            f"sqlite:///{PRODUCTION_DB_PATH}",
            connect_args={"timeout": DB_CONNECTION_TIMEOUT},
            pool_size=DB_CONNECTION_POOL_SIZE,
            max_overflow=DB_CONNECTION_MAX_OVERFLOW,
            pool_pre_ping=True,  # Test connections before using them
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False  # Set to True for debugging SQL queries
        )
        
        # Test connection with retry logic
        for attempt in range(DB_CONNECTION_RETRY_ATTEMPTS):
            try:
                with engine.connect() as conn:
                    result = conn.execute("SELECT 1")
                    result.fetchone()
                logger.info(f"Production database connection established successfully on attempt {attempt + 1}.")
                break
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == DB_CONNECTION_RETRY_ATTEMPTS - 1:
                    raise RuntimeError(f"Database connection failed after {DB_CONNECTION_RETRY_ATTEMPTS} attempts: {e}")
                # Wait before retry (exponential backoff)
                import time
                time.sleep(2 ** attempt)
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to connect to production database: {e}")
        raise RuntimeError(f"Database connection failed: {e}")

# Initialize production engine (lazy loading)
_production_engine = None

def get_engine():
    """Get or create production database engine."""
    global _production_engine
    if _production_engine is None:
        _production_engine = get_production_engine()
    return _production_engine


class QueryValidator:
    """Input validation and sanitization for SQL queries."""
    
    @staticmethod
    def validate_query_length(query: str) -> bool:
        """Validate query length is within acceptable bounds."""
        return MIN_QUERY_LENGTH <= len(query) <= MAX_QUERY_LENGTH
    
    @staticmethod
    def detect_sql_injection(query: str) -> Optional[str]:
        """Detect potential SQL injection attempts."""
        query_lower = query.lower()
        
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return f"Potential SQL injection detected: matches pattern '{pattern}'"
        
        return None
    
    @staticmethod
    def sanitize_input(query: str) -> str:
        """Sanitize user input to prevent XSS and other attacks."""
        # Remove HTML tags
        query = re.sub(r'<[^>]+>', '', query)
        
        # Escape HTML entities
        query = html.escape(query)
        
        # Remove excessive whitespace
        query = ' '.join(query.split())
        
        # Validate against allowed characters
        if not re.match(ALLOWED_SPECIAL_CHARS, query):
            # Remove disallowed characters
            query = re.sub(r'[^\w\s.,!?;:\-\'"()]', '', query)
        
        return query.strip()
    
    @staticmethod
    def validate_content(query: str) -> Optional[str]:
        """Validate query content for appropriateness and safety."""
        # Check for empty or whitespace-only queries
        if not query or not query.strip():
            return "Query cannot be empty"
        
        # Check for excessive repetition (potential spam/bot behavior)
        words = query.lower().split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any word appears more than 30% of the time, flag as suspicious
            for word, count in word_counts.items():
                if count / len(words) > 0.3 and len(word) > 2:
                    return "Query contains excessive repetition"
        
        # Check for potential malicious content patterns
        malicious_patterns = [
            r'\b(hack|exploit|vulnerability|bypass|inject)\b',
            r'\b(admin|root|system|database|schema)\b.*\b(password|access|login)\b',
            r'\b(drop|delete|truncate|destroy)\b.*\b(all|everything|database)\b'
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return "Query contains potentially malicious content"
        
        return None
    
    @staticmethod
    def validate_query(query: str) -> Dict[str, Any]:
        """Comprehensive query validation."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "sanitized_query": query
        }
        
        # Length validation
        if not QueryValidator.validate_query_length(query):
            validation_result["errors"].append(
                f"Query length must be between {MIN_QUERY_LENGTH} and {MAX_QUERY_LENGTH} characters"
            )
            validation_result["valid"] = False
        
        # SQL injection detection
        injection_error = QueryValidator.detect_sql_injection(query)
        if injection_error:
            validation_result["errors"].append(injection_error)
            validation_result["valid"] = False
        
        # Content validation
        content_error = QueryValidator.validate_content(query)
        if content_error:
            validation_result["errors"].append(content_error)
            validation_result["valid"] = False
        
        # Sanitization (always performed)
        sanitized = QueryValidator.sanitize_input(query)
        if sanitized != query:
            validation_result["warnings"].append("Query was sanitized for safety")
            validation_result["sanitized_query"] = sanitized
        
        return validation_result


class QueryMetrics:
    """Track query metrics for monitoring and rate limiting."""
    
    def __init__(self):
        self.query_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
    
    def record_query(self, success: bool, processing_time: float):
        """Record query execution metrics."""
        self.query_count += 1
        if not success:
            self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "total_queries": self.query_count,
            "error_count": self.error_count,
            "success_rate": (self.query_count - self.error_count) / max(self.query_count, 1),
            "uptime_seconds": uptime,
            "queries_per_second": self.query_count / max(uptime, 1)
        }


# Global metrics instance
query_metrics = QueryMetrics()


@tool
def sql_query_tool(user_query_str: str) -> str:
    """Use this tool to answer questions from querying the SQL database.
    
    Args:
        user_query_str (str): The user's query string in natural language.
        
    Returns:
        str: The answer from the SQL database.
        
    Raises:
        ValueError: If the query is invalid or unsafe
        RuntimeError: If database operations fail
    """
    start_time = datetime.now()
    correlation_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{correlation_id}] Processing SQL query: {user_query_str[:100]}...")
        
        # Validate input
        validation_result = QueryValidator.validate_query(user_query_str)
        
        if not validation_result["valid"]:
            error_msg = f"Query validation failed: {'; '.join(validation_result['errors'])}"
            logger.warning(f"[{correlation_id}] {error_msg}")
            query_metrics.record_query(False, 0)
            raise ValueError(error_msg)
        
        # Use sanitized query
        sanitized_query = validation_result["sanitized_query"]
        
        if validation_result["warnings"]:
            logger.info(f"[{correlation_id}] Query warnings: {'; '.join(validation_result['warnings'])}")
        
        # Initialize database connection
        production_engine = get_engine()
        sql_database = SQLDatabase(
            production_engine, include_tables=PRODUCTION_TABLES
        )
        
        # Create connector instance
        connector = LlamaIndexConnector(
            sql_database=sql_database,
            llm=llama_index_llm,
            embed_model=fireworks_embed_model,
        )
        
        # Execute query
        result = connector.user_query_with_retrieval(sanitized_query)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        query_metrics.record_query(True, processing_time)
        
        logger.info(f"[{correlation_id}] Query completed successfully in {processing_time:.2f}s")
        
        return result
        
    except ValueError:
        # Re-raise validation errors
        raise
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        query_metrics.record_query(False, processing_time)
        
        error_msg = f"Database query failed: {str(e)}"
        logger.error(f"[{correlation_id}] {error_msg}")
        
        # Provide user-friendly error message
        if "connection" in str(e).lower():
            raise RuntimeError("Unable to connect to the database. Please try again later.")
        elif "timeout" in str(e).lower():
            raise RuntimeError("Query timeout exceeded. Please try a simpler query.")
        else:
            raise RuntimeError("An error occurred while processing your query. Please try again.")


def get_query_metrics() -> Dict[str, Any]:
    """Get query execution metrics for monitoring."""
    return query_metrics.get_metrics()


def health_check() -> Dict[str, Any]:
    """Perform health check on the SQL query tool."""
    try:
        # Test database connection
        production_engine = get_engine()
        sql_database = SQLDatabase(production_engine, include_tables=PRODUCTION_TABLES)
        
        # Simple test query
        with production_engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()
        
        return {
            "status": "healthy",
            "database_connected": True,
            "tables_available": PRODUCTION_TABLES,
            "metrics": get_query_metrics(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Export main components
__all__ = ['sql_query_tool', 'get_query_metrics', 'health_check', 'QueryValidator', 'QueryMetrics']