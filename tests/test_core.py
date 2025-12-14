"""Unit tests for `TextToSQL` placeholder behavior."""

import pytest

from text2sql.core import TextToSQL


def test_texttosql_run_not_implemented():
    t2s = TextToSQL()
    with pytest.raises(NotImplementedError):
        t2s.run("Show me users")
