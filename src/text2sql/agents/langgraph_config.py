"""LangGraph configuration placeholders.

This will contain code to build and register LangGraph graphs, nodes, and
connectors for orchestrating the Text->SQL pipeline.
"""

DEFAULT_CONFIG = {
    "langgraph": {
        "graph_name": "text2sql_graph",
        "nodes": [],
    }
}

# TODO: add functions to generate LangGraph objects from this config
