import pytest
from unittest.mock import MagicMock, patch
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


@patch("scrapeddit.utils.db_utils.console")
def test_db_execute_prints_rows_affected(mock_console, mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.description = None
    mock_cursor.rowcount = 3

    mod.db_execute(mock_conn, "UPDATE x")

    mock_console.print.assert_called_once_with("Query OK, 3 rows affected.")


@patch("scrapeddit.utils.db_utils.console")
def test_db_execute_exception(mock_console, mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.execute.side_effect = ValueError("bad sql")

    mod.db_execute(mock_conn, "SELECT bad")

    mock_console.print.assert_called_once_with("builtins.ValueError: bad sql")


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


def test_insert_submission(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()

    submission_data = {
        "name": "t3_abcdef",
        "author": "testuser",
        "title": "Test Submission",
        "selftext": "This is a test submission.",
        "url": "https://reddit.com/r/testsubreddit/comments/abcdef/test_submission/",
        "created_utc": 1620000000,
        "edited": False,
        "ups": 100,
        "subreddit": "r/testsubreddit",
        "permalink": "/r/testsubreddit/comments/abcdef/test_submission/",
    }

    mod.insert_submission(mock_conn, submission_data)

    mock_cursor.execute.assert_called_once()


def test_insert_submission_overwrite(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()

    submission_data = {
        "name": "t3_ghijkl",
        "author": "anotheruser",
        "title": "Another Test Submission",
        "selftext": "This is another test submission.",
        "url": "https://reddit.com/r/testsubreddit/comments/ghijkl/another_test_submission/",
        "created_utc": 1620001000,
        "edited": True,
        "ups": 150,
        "subreddit": "r/testsubreddit",
        "permalink": "/r/testsubreddit/comments/ghijkl/another_test_submission/",
    }

    mod.insert_submission(mock_conn, submission_data, overwrite=True)

    mock_cursor.execute.assert_called_once()


def test_insert_comment(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()

    comment_data = {
        "name": "t1_abcdef",
        "author": "commentuser",
        "body": "This is a test comment.",
        "created_utc": 1620002000,
        "edited": False,
        "ups": 50,
        "parent_id": "t3_abcdef",
        "submission_id": "t3_abcdef",
        "subreddit": "r/testsubreddit",
    }

    mod.insert_comment(mock_conn, comment_data)

    mock_cursor.execute.assert_called_once()


def test_insert_comment_overwrite(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.execute = MagicMock()

    comment_data = {
        "name": "t1_ghijkl",
        "author": "anothercommenter",
        "body": "This is another test comment.",
        "created_utc": 1620003000,
        "edited": True,
        "ups": 75,
        "parent_id": "t3_ghijkl",
        "submission_id": "t3_ghijkl",
        "subreddit": "r/testsubreddit",
    }

    mod.insert_comment(mock_conn, comment_data, overwrite=True)

    mock_cursor.execute.assert_called_once()


def test_batch_insert_comments(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.executemany = MagicMock()

    comments_data = [
        (
            "t1_abcdef",
            "commenter1",
            "First batch comment.",
            1620004000,
            False,
            20,
            "t3_abcdef",
            "t3_abcdef",
            "r/testsubreddit",
        ),
        (
            "t1_ghijkl",
            "commenter2",
            "Second batch comment.",
            1620005000,
            False,
            30,
            "t3_abcdef",
            "t3_abcdef",
            "r/testsubreddit",
        ),
    ]

    mod.batch_insert_comments(mock_conn, comments_data)

    mock_cursor.executemany.assert_called_once()


def test_batch_insert_comments_overwrite(mock_with_resources):
    mod = mock_with_resources

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False

    mock_cursor.executemany = MagicMock()

    comments_data = [
        (
            "t1_mnopqr",
            "commenter3",
            "Third batch comment.",
            1620006000,
            True,
            40,
            "t3_ghijkl",
            "t3_ghijkl",
            "r/testsubreddit",
        ),
        (
            "t1_stuvwx",
            "commenter4",
            "Fourth batch comment.",
            1620007000,
            True,
            50,
            "t3_ghijkl",
            "t3_ghijkl",
            "r/testsubreddit",
        ),
    ]

    mod.batch_insert_comments(mock_conn, comments_data, overwrite=True)

    mock_cursor.executemany.assert_called_once()
