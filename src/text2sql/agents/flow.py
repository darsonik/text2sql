"""Placeholders for LangGraph flows and agent setup.

Add LangGraph flows that coordinate retrieval (LlamaIndex) + SQL generation steps.
"""

# TODO: Import LangGraph components and define flows

class AgentFlow:
    """High-level orchestrator placeholder for agent flows."""

    def __init__(self, config=None):
        self.config = config

    def run(self, query: str):
        """Execute the flow for a user query.

        Returns NotImplemented for now.
        """
        raise NotImplementedError()
