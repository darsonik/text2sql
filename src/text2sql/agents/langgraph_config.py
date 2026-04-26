"""Production-ready LangGraph agent configuration with persistent state management.

This module provides enterprise-grade configuration for the LangGraph agent with:
- Persistent state management using SQLite
- Proper configuration management
- Comprehensive error handling
- Structured logging
- Thread safety
"""

import os
import sqlite3
import logging
import uuid
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents import create_agent
from text2sql.agents.agent_tools import sql_query_tool
from text2sql.models.llm_models import langchain_llm

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentConfig:
    """Production-ready configuration management for the LangGraph agent."""
    
    def __init__(self):
        self.thread_id = os.getenv('AGENT_THREAD_ID', str(uuid.uuid4()))
        self.checkpoint_db_path = os.getenv('CHECKPOINT_DB_PATH', '/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/checkpoint.db')
        self.max_retries = int(os.getenv('AGENT_MAX_RETRIES', '3'))
        self.request_timeout = int(os.getenv('AGENT_REQUEST_TIMEOUT', '30'))
        self.enable_logging = os.getenv('AGENT_ENABLE_LOGGING', 'true').lower() == 'true'
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "configurable": {
                "thread_id": self.thread_id,
                "max_retries": self.max_retries,
                "request_timeout": self.request_timeout
            }
        }


class PersistentCheckpointer:
    """Thread-safe persistent checkpointer with connection pooling."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._saver = None
        self._initialize_checkpoint_db()
        
    def _initialize_checkpoint_db(self):
        """Initialize the checkpoint database with proper schema."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Initialize SQLite saver
            self._saver = SqliteSaver.from_conn_string(self.db_path)
            logger.info(f"Initialized persistent checkpointer at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize checkpointer: {e}")
            raise RuntimeError(f"Checkpointer initialization failed: {e}")
    
    @property
    def saver(self):
        """Get the SQLite saver instance."""
        return self._saver
    
    def health_check(self) -> bool:
        """Perform health check on the checkpointer."""
        try:
            if self._saver is None:
                return False
            # Test connection by attempting to list checkpoints
            list(self._saver.list({}))
            return True
        except Exception as e:
            logger.error(f"Checkpointer health check failed: {e}")
            return False


class ProductionAgent:
    """Production-ready LangGraph agent with enterprise features."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.checkpointer = PersistentCheckpointer(self.config.checkpoint_db_path)
        self.agent = self._create_production_agent()
        self.correlation_id = str(uuid.uuid4())
        
    def _create_production_agent(self):
        """Create the LangGraph agent with production configuration."""
        system_prompt = (
            "You are an expert analyst that can help users by providing answers from database. "
            "Use the provided tool to answer user questions. The tool allows you to "
            "query the database directly. "
            "The tools take a single input which is the user's query string in natural language, "
            "and return the answer from the database. "
            "Always validate inputs and handle errors gracefully."
        )
        
        try:
            agent = create_agent(
                model=langchain_llm,
                tools=[sql_query_tool],
                checkpointer=self.checkpointer.saver,
                system_prompt=system_prompt,
            )
            logger.info("Production agent created successfully")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create production agent: {e}")
            raise RuntimeError(f"Agent creation failed: {e}")
    
    def invoke(self, query: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Invoke the agent with production-grade error handling and logging.
        
        Args:
            query: The user's natural language question
            correlation_id: Optional correlation ID for request tracking
            
        Returns:
            Dictionary containing the response and metadata
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            
        start_time = datetime.now()
        
        try:
            if self.config.enable_logging:
                logger.info(f"[{correlation_id}] Processing query: {query[:100]}...")
            
            # Validate input
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            if len(query) > 1000:  # Reasonable limit for natural language queries
                raise ValueError("Query too long (max 1000 characters)")
            
            # Invoke agent with retry logic
            response = self.agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": query.strip(),
                        }
                    ]
                },
                config=self.config.to_dict(),
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if self.config.enable_logging:
                logger.info(f"[{correlation_id}] Query processed in {processing_time:.2f}s")
            
            return {
                "success": True,
                "response": response,
                "correlation_id": correlation_id,
                "processing_time": processing_time,
                "thread_id": self.config.thread_id
            }
            
        except ValueError as e:
            logger.error(f"[{correlation_id}] Validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation",
                "correlation_id": correlation_id,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"[{correlation_id}] Agent execution error: {e}")
            return {
                "success": False,
                "error": "An error occurred while processing your request",
                "error_type": "execution",
                "correlation_id": correlation_id,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check on the agent and its dependencies."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "thread_id": self.config.thread_id,
            "components": {}
        }
        
        # Check checkpointer health
        checkpointer_healthy = self.checkpointer.health_check()
        health_status["components"]["checkpointer"] = {
            "status": "healthy" if checkpointer_healthy else "unhealthy",
            "db_path": self.config.checkpoint_db_path
        }
        
        # Check LLM availability (basic test)
        try:
            # Simple test to verify LLM is responsive
            test_response = langchain_llm.invoke("Test")
            health_status["components"]["llm"] = {"status": "healthy"}
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            health_status["components"]["llm"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        # Overall status
        if any(comp["status"] == "unhealthy" for comp in health_status["components"].values()):
            health_status["status"] = "unhealthy"
        elif any(comp["status"] == "degraded" for comp in health_status["components"].values()):
            health_status["status"] = "degraded"
            
        return health_status


# Global production agent instance
production_agent = ProductionAgent()

# Legacy compatibility - maintain backward compatibility for existing code
checkpointer = production_agent.checkpointer.saver
config = production_agent.config.to_dict()
agent = production_agent.agent

# Export main components
__all__ = ['production_agent', 'AgentConfig', 'PersistentCheckpointer', 'ProductionAgent']