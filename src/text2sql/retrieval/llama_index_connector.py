"""Placeholder for LlamaIndex connector logic.

This module will handle building or loading an index from schema docs and
performing retrieval for queries that feed into the agent flow.
"""

class LlamaIndexConnector:
    """Placeholder wrapper for llama-index related functionality."""

    def __init__(self, index_path: str = None):
        self.index_path = index_path

    def build_index(self, documents):
        """Build index from a sequence of documents. TODO implement."""
        raise NotImplementedError()

    def query(self, prompt: str):
        """Query the index and return hits. TODO implement."""
        raise NotImplementedError()
