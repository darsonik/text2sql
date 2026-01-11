"""Tests for `LlamaIndexConnector` placeholder."""

import pytest

from src.text2sql.retrieval.llama_index_connector import LlamaIndexConnector


def test_build_index_not_implemented():
    c = LlamaIndexConnector()
    with pytest.raises(NotImplementedError):
        c.build_index([])


def test_query_not_implemented():
    c = LlamaIndexConnector()
    with pytest.raises(NotImplementedError):
        c.query("select * from users")
