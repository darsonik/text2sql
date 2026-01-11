"""Tests for `LlamaIndexConnector` placeholder."""

import pytest
from unittest.mock import Mock

from text2sql.retrieval.llama_index_connector import LlamaIndexConnector


@pytest.fixture
def connector():
    """Fixture to create a LlamaIndexConnector with mock dependencies."""
    mock_db = Mock()
    mock_llm = Mock()
    mock_embed = Mock()
    return LlamaIndexConnector(mock_db, mock_llm, mock_embed)


def test_build_index_not_implemented(connector):
    with pytest.raises(NotImplementedError):
        connector.build_index([])


def test_query_not_implemented(connector):
    with pytest.raises(NotImplementedError):
        connector.query("select * from users")
