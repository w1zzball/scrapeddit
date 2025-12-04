import pytest
from unittest.mock import MagicMock, patch
import scrapeddit.utils.scraping_utils as mod


# patch decorator
@pytest.fixture(autouse=True)
def mock_with_resources():
    # no-op decorator
    def fake_with_resources(*a, **kw):
        def decorator(func):
            return func

        return decorator

    with pytest.MonkeyPatch.context() as mp:

        mp.setattr(mod, "with_resources", fake_with_resources)
        yield


# functions must be patched from where they are used,
#  not where they are defined
@patch("scrapeddit.utils.scraping_utils.console")
@patch("scrapeddit.utils.scraping_utils.insert_submission")
@patch("scrapeddit.utils.scraping_utils.format_submission")
@patch("scrapeddit.utils.scraping_utils.get_submission")
def test_scrape_submission_success(
    mock_get,
    mock_format,
    mock_insert,
    mock_console,
):
    mock_get.return_value = {"id": "abc"}
    mock_format.return_value = {"id": "abc", "formatted": True}
    mock_insert.return_value = ("abc",)

    mod.scrape_submission(post_id="abc")

    mock_get.assert_called_once_with("abc", None)
    mock_format.assert_called_once_with({"id": "abc"})
    mock_insert.assert_called_once_with({"id": "abc", "formatted": True})
    mock_console.print.assert_called_once_with(
        "Inserted/updated submission abc"
    )


@patch("scrapeddit.utils.scraping_utils.console")
@patch("scrapeddit.utils.scraping_utils.insert_submission", return_value=None)
@patch("scrapeddit.utils.scraping_utils.format_submission")
@patch("scrapeddit.utils.scraping_utils.get_submission")
def test_scrape_submission_no_change(
    mock_get,
    mock_format,
    mock_insert,
    mock_console,
):
    mod.scrape_submission(post_id="abc")

    mock_console.print.assert_called_once_with(
        "No change to submission (conflict and skipped)"
    )


@patch("scrapeddit.utils.scraping_utils.console")
@patch(
    "scrapeddit.utils.scraping_utils.insert_submission", return_value=("abc",)
)
@patch("scrapeddit.utils.scraping_utils.format_submission")
@patch("scrapeddit.utils.scraping_utils.get_submission")
def test_scrape_submission_prefix(
    mock_get,
    mock_format,
    mock_insert,
    mock_console,
):
    mod.scrape_submission(post_id="abc", index=3, total=10)

    mock_console.print.assert_called_once_with(
        "[3/10] Inserted/updated submission abc"
    )


@patch("scrapeddit.utils.scraping_utils.console")
@patch("scrapeddit.utils.scraping_utils.insert_comment")
@patch("scrapeddit.utils.scraping_utils.format_comment")
@patch("scrapeddit.utils.scraping_utils.get_comment")
def test_scrape_comment(
    mock_get_comment,
    mock_format_comment,
    mock_insert_comment,
    mock_console,
):

    # arrange
    mock_get_comment.return_value = {"id": "def"}
    mock_format_comment.return_value = {"id": "def", "formatted": True}
    mock_insert_comment.return_value = ("def",)

    # act
    mod.scrape_comment(comment_id="def")

    # assert
    mock_get_comment.assert_called_once_with("def")
    mock_format_comment.assert_called_once_with({"id": "def"})
    mock_insert_comment.assert_called_once_with(
        {"id": "def", "formatted": True}
    )
    mock_console.print.assert_called_once_with("Inserted/updated comment def")


@patch("scrapeddit.utils.scraping_utils.console")
@patch("scrapeddit.utils.scraping_utils.insert_comment")
@patch("scrapeddit.utils.scraping_utils.format_comment")
@patch("scrapeddit.utils.scraping_utils.get_comment")
def test_scrape_comment_no_change(
    mock_get_comment,
    mock_format_comment,
    mock_insert_comment,
    mock_console,
):

    mock_insert_comment.return_value = None
    mod.scrape_comment(comment_id="def")

    mock_console.print.assert_called_once_with(
        "No change to comment (conflict and skipped)"
    )


# @patch("scrapeddit.utils.scraping_utils.console")
# @patch("scrapeddit.utils.scraping_utils.insert_comment")
# @patch("scrapeddit.utils.scraping_utils.format_comment")
# @patch("scrapeddit.utils.scraping_utils.get_comments_in_thread")
# def test_scrape_comments_in_thread_success(
#     mock_get_comments_in_thread,
#     mock_format_comment,
#     mock_insert_comment,
#     mock_console,
# ):
#     mock_get_comments_in_thread.return_value = {"id": "def"}
#     mock_format_comment.return_value = {"id": "def", "formatted": True}
#     mock_insert_comment.return_value = ("def",)

#     mod.scrape_comments_in_thread(thread_id="ghi", limit=5)

#     mock_get_comments_in_thread.assert_called_once_with(
#         "def", thread_id="ghi", limit=5
#     )
#     mock_format_comment.assert_called_once_with({"id": "def"})
#     mock_insert_comment.assert_called_once_with(
#         {"id": "def", "formatted": True}
#     )
#     mock_console.print.assert_called_once_with(
#         "Inserted/updated 1 comments from thread ghi"
#     )


@patch("scrapeddit.utils.scraping_utils.scrape_submission")
@patch("scrapeddit.utils.scraping_utils.scrape_comments_in_thread")
def test_scrape_entire_thread(
    mock_scrape_comments_in_thread,
    mock_scrape_submission,
):
    mod.scrape_entire_thread(thread_id="xyz", comment_limit=10)

    mock_scrape_submission.assert_called_once()
    mock_scrape_comments_in_thread.assert_called_once()


@patch("scrapeddit.utils.scraping_utils.console")
@patch("scrapeddit.utils.scraping_utils.batch_insert_comments")
@patch("scrapeddit.utils.scraping_utils.format_comment")
@patch("scrapeddit.utils.scraping_utils.get_redditors_comments")
def test_scrape_redditor(
    mock_get_redditors_comments,
    mock_format_comment,
    mock_batch_insert_comments,
    mock_console,
):

    mock_get_redditors_comments.return_value = [
        {"id": "a"},
        {"id": "b"},
    ]

    mod.scrape_redditor("test_user")

    mock_get_redditors_comments.assert_called_once_with(
        "test_user", 100, sort="new"
    )

    assert mock_format_comment.call_count == 2

    mock_batch_insert_comments.assert_called_once()

    mock_console.print.assert_called()


@patch("scrapeddit.utils.scraping_utils.console")
@patch("scrapeddit.utils.scraping_utils.batch_insert_comments")
@patch("scrapeddit.utils.scraping_utils.format_comment")
@patch("scrapeddit.utils.scraping_utils.get_redditors_comments")
def test_scrape_redditor_get_comment_exception(
    mock_get_redditors_comments,
    mock_format_comment,
    mock_batch_insert_comments,
    mock_console,
):
    mock_get_redditors_comments.side_effect = Exception("fail")
    mod.scrape_redditor("test_user")
    mock_console.print.assert_called_once_with(
        "[red]Error scraping u/test_user: fail[/red]"
    )


@patch("scrapeddit.utils.scraping_utils.scrape_redditor")
def test_scrape_redditors_success(mock_scrape_redditor):
    redditor_list = ["user1", "user2", "user3"]
    mod.scrape_redditors(redditor_list)
    assert mock_scrape_redditor.call_count == 3


@patch("scrapeddit.utils.scraping_utils.scrape_redditor")
@patch("scrapeddit.utils.scraping_utils.console")
def test_scrape_redditors_exception(mock_console, mock_scrape_redditor):
    mock_scrape_redditor.side_effect = Exception("fail")
    redditor_list = ["user1", "user2"]
    mod.scrape_redditors(redditor_list)
    assert mock_scrape_redditor.call_count == 2
    mock_console.print.assert_called_with(
        "[red]Error scraping u/user2: fail[/red]"
    )


# @patch("scrapeddit.utils.scraping_utils.console")
# @patch("scrapeddit.utils.scraping_utils.scrape_redditor")
# def test_expand_redditors_comments(mock_scrape_redditor, mock_console):
#     mock_conn = MagicMock()
#     mock_cursor = MagicMock()

#     mock_cursor.execute = MagicMock()
#     mock_cursor.fetchall.return_value = [("user1",), ("user2",), ("user3",)]

#     mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
#     mock_conn.cursor.return_value.__exit__.return_value = False

#     mod.expand_redditors_comments(threshold=10, limit=5)
#     mock_cursor.execute.assert_called_once()
