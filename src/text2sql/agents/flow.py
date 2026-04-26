"""Production-ready LangGraph flows and agent orchestration.

This module provides enterprise-grade orchestration for agent flows with:
- Production agent integration
- Comprehensive error handling
- Request tracking and correlation IDs
- Performance monitoring
- Graceful degradation
"""

import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from text2sql.agents.langgraph_config import production_agent, AgentConfig

# Configure logging
logger = logging.getLogger(__name__)


class AgentFlow:
    """Production-ready high-level orchestrator for agent flows based on LangGraph."""
    
    def __init__(self, config: Optional[AgentConfig] = None, correlation_id: Optional[str] = None):
        """Initialize the agent flow with production configuration.
        
        Args:
            config: Optional custom configuration for the agent
            correlation_id: Optional correlation ID for request tracking
        """
        self.config = config or AgentConfig()
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.agent = production_agent
        self.start_time = None
        
        logger.info(f"[{self.correlation_id}] AgentFlow initialized with thread_id: {self.config.thread_id}")
    
    def run(self, query: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the flow for a user query with production-grade error handling.
        
        Args:
            query: The user's natural language question
            correlation_id: Optional correlation ID for request tracking
            
        Returns:
            Dictionary containing the response and metadata, or error information
        """
        if correlation_id:
            self.correlation_id = correlation_id
            
        self.start_time = datetime.now()
        
        try:
            logger.info(f"[{self.correlation_id}] Processing query: {query[:100]}...")
            
            # Use the production agent's invoke method for comprehensive error handling
            result = self.agent.invoke(query, correlation_id=self.correlation_id)
            
            if result["success"]:
                # Extract the final answer from the response
                response_messages = result["response"]["messages"]
                final_answer = response_messages[-1].content if response_messages else "No response generated"
                
                processing_time = (datetime.now() - self.start_time).total_seconds() if self.start_time else result.get("processing_time", 0)
                
                logger.info(f"[{self.correlation_id}] Query completed successfully in {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "response": final_answer,
                    "correlation_id": self.correlation_id,
                    "processing_time": processing_time,
                    "thread_id": result.get("thread_id", self.config.thread_id),
                    "metadata": {
                        "query_length": len(query),
                        "response_length": len(final_answer),
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                # Handle agent errors gracefully
                logger.error(f"[{self.correlation_id}] Agent execution failed: {result.get('error', 'Unknown error')}")
                
                processing_time = (datetime.now() - self.start_time).total_seconds() if self.start_time else result.get("processing_time", 0)
                
                return {
                    "success": False,
                    "error": result.get("error", "An error occurred while processing your request"),
                    "error_type": result.get("error_type", "unknown"),
                    "correlation_id": self.correlation_id,
                    "processing_time": processing_time,
                    "thread_id": result.get("thread_id", self.config.thread_id),
                    "suggestion": "Please try rephrasing your question or contact support if the issue persists."
                }
                
        except Exception as e:
            logger.error(f"[{self.correlation_id}] Unexpected error in AgentFlow: {e}")
            
            processing_time = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return {
                "success": False,
                "error": "An unexpected error occurred while processing your request",
                "error_type": "system",
                "correlation_id": self.correlation_id,
                "processing_time": processing_time,
                "thread_id": self.config.thread_id,
                "suggestion": "Please try again later or contact support."
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the agent flow and its dependencies.
        
        Returns:
            Health status dictionary with component details
        """
        logger.info(f"[{self.correlation_id}] Performing health check")
        
        try:
            agent_health = self.agent.health_check()
            
            health_status = {
                "status": agent_health["status"],
                "timestamp": datetime.now().isoformat(),
                "correlation_id": self.correlation_id,
                "thread_id": self.config.thread_id,
                "components": {
                    "agent_flow": {"status": "healthy"},
                    "agent": agent_health
                }
            }
            
            logger.info(f"[{self.correlation_id}] Health check completed: {health_status['status']}")
            return health_status
            
        except Exception as e:
            logger.error(f"[{self.correlation_id}] Health check failed: {e}")
            
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "correlation_id": self.correlation_id,
                "thread_id": self.config.thread_id,
                "components": {
                    "agent_flow": {"status": "unhealthy", "error": str(e)}
                },
                "error": "Health check failed"
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the agent flow.
        
        Returns:
            Dictionary containing performance metrics
        """
        return {
            "correlation_id": self.correlation_id,
            "thread_id": self.config.thread_id,
            "config": {
                "max_retries": self.config.max_retries,
                "request_timeout": self.config.request_timeout,
                "enable_logging": self.config.enable_logging
            },
            "timestamp": datetime.now().isoformat()
        }


# Legacy compatibility - maintain backward compatibility for existing code
# This provides a drop-in replacement for the original AgentFlow
class LegacyAgentFlow:
    """Legacy compatibility wrapper for backward compatibility."""
    
    def __init__(self, config=None):
        self.flow = AgentFlow(config=config)
    
    def run(self, query: str):
        """Legacy run method that returns just the response string."""
        result = self.flow.run(query)
        if result["success"]:
            return result["response"]
        else:
            raise RuntimeError(f"Agent execution failed: {result.get('error', 'Unknown error')}")


# Export the production-ready classes
__all__ = ['AgentFlow', 'LegacyAgentFlow']