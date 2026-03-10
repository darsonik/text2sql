"""LangGraph flows and agent setup orchestration.

This module provides an abstraction over the LangGraph agent for easy execution.
"""

from text2sql.agents.langgraph_config import agent


class AgentFlow:
    """High-level orchestrator for agent flows based on LangGraph."""

    def __init__(self, config=None):
        self.config = config or {"configurable": {"thread_id": "demo"}}
        self.agent = agent

    def run(self, query: str):
        """Execute the flow for a user query.

        Args:
            query: The user's natural language question.

        Returns:
            The final answer string from the AI agent.
        """
        response = self.agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query,
                    }
                ]
            },
            config=self.config,
        )
        return response["messages"][-1].content
