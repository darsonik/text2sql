"""Sanity tests to make sure package imports and placeholders exist."""

import pytest


def test_import_core():
    import text2sql.core as core  # noqa: F401


def test_import_agents():
    import text2sql.agents.flow as flow  # noqa: F401


def test_import_retrieval():
    import text2sql.retrieval.llama_index_connector as conn  # noqa: F401
