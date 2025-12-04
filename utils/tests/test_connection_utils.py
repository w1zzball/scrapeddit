import pytest
from unittest.mock import MagicMock, patch
import scrapeddit.utils.connection_utils as mod


def test_reddit_session_success():
    mock_reddit = MagicMock()

    with patch(
        "scrapeddit.utils.connection_utils.praw.Reddit",
        return_value=mock_reddit,
    ):
        with mod.reddit_session() as reddit:
            assert reddit == mock_reddit


def test_db_connection_success():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "scrapeddit.utils.connection_utils.psycopg.connect",
        return_value=mock_conn,
    ):
        with mod.db_connection(schema="test_schema") as conn:
            assert conn == mock_conn
            mock_cursor.execute.assert_called_once_with(
                'SET search_path TO "test_schema"'
            )
    mock_conn.close.assert_called_once()


# testing wrapper requires applying to dummy functions


def test_with_resources_both():
    mock_reddit = MagicMock()
    mock_conn = MagicMock()

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_r, patch(
        "scrapeddit.utils.connection_utils.db_connection"
    ) as mock_db:

        mock_r.return_value.__enter__.return_value = mock_reddit
        mock_db.return_value.__enter__.return_value = mock_conn

        @mod.with_resources(use_reddit=True, use_db=True)
        def fn(conn, reddit, x):
            return (conn, reddit, x)

        result = fn("hello")

        mock_r.assert_called_once()
        mock_db.assert_called_once()

        assert result == (mock_reddit, mock_conn, "hello")


def test_with_resources_only_db():
    mock_conn = MagicMock()

    with patch("scrapeddit.utils.connection_utils.db_connection") as mock_db:

        mock_db.return_value.__enter__.return_value = mock_conn

        @mod.with_resources(use_reddit=False, use_db=True)
        def fn(conn, x):
            return (conn, x)

        result = fn("hello")

        mock_db.assert_called_once()

        assert result == (mock_conn, "hello")


def test_with_resources_neither():
    @mod.with_resources(use_reddit=False, use_db=False)
    def fn(x):
        return x

    result = fn("hello")

    assert result == "hello"
