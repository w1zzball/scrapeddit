import pytest
from unittest.mock import MagicMock
import importlib


# module has to be reloaded after patching
# to correctly return faked with_resources
@pytest.fixture(autouse=True)
def mock_with_resources(monkeypatch):
    def fake_with_resources(*a, **kw):
        def decorator(func):
            return func

        return decorator

    monkeypatch.setattr(
        "scrapeddit.utils.connection_utils.with_resources", fake_with_resources
    )

    import scrapeddit.utils.db_utils as mod

    importlib.reload(mod)

    return mod  # return patched module


def test_db_execute(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = ("col",)

    sql = "SELECT 1;"

    mod.db_execute(mock_conn, sql)

    mock_cursor.execute.assert_called_once_with(sql)


def test_db_execute_prints_rows_affected(mock_with_resources, capsys):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.description = None
    mock_cursor.rowcount = 3
    mock_cursor.execute = MagicMock()

    mod.db_execute(mock_conn, "UPDATE x")

    # check print statement
    out = capsys.readouterr().out
    assert "Query OK, 3 rows affected." in out


def test_db_execute_exception(mock_with_resources, capsys):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # context manager
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    # force error inside execute
    mock_cursor.execute.side_effect = ValueError("bad sql")

    mod.db_execute(mock_conn, "SELECT bad")

    out = capsys.readouterr().out
    assert "ValueError: bad sql" in out


def test_clear_all_tables(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False
    mock_cursor.execute = MagicMock()
    mock_cursor.rowcount = 5
    submissions_deleted, comments_deleted = mod.clear_tables(
        mock_conn, target="all"
    )
    assert submissions_deleted == 5
    assert comments_deleted == 5


def test_db_get_redditors_from_subreddit(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()
    mock_cursor.fetchall.return_value = [("user1",), ("user2",), ("user3",)]

    redditors = mod.db_get_redditors_from_subreddit(
        mock_conn, "testsubreddit", limit=3
    )

    mock_cursor.execute.assert_called_once()
    assert redditors == ["user1", "user2", "user3"]


def test_db_get_redditors_from_subreddit_with_r_prefix(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()
    mock_cursor.fetchall.return_value = [("userA",), ("userB",)]

    redditors = mod.db_get_redditors_from_subreddit(
        mock_conn, "r/testsubreddit", limit=2
    )

    mock_cursor.execute.assert_called_once()
    assert redditors == ["userA", "userB"]
