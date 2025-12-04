import pytest
from unittest.mock import MagicMock, patch
import scrapeddit.utils.reddit_utils as mod


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


def test_format_submission():
    mock_submission = MagicMock()
    mock_submission.name = "t3_abcdef"
    mock_submission.author = "test_user"
    mock_submission.title = "Test Title"
    mock_submission.selftext = "This is a test selftext."
    mock_submission.url = "https://reddit.com/test_post"
    mock_submission.created_utc = 1609459200
    mock_submission.edited = False
    mock_submission.ups = 100
    mock_submission.subreddit = "testsubreddit"
    mock_submission.permalink = "/r/testsubreddit/comments/abcdef/test_title/"

    formatted = mod.format_submission(mock_submission)

    assert formatted["name"] == "t3_abcdef"
    assert formatted["author"] == "test_user"
    assert formatted["title"] == "Test Title"
    assert formatted["selftext"] == "This is a test selftext."
    assert formatted["url"] == "https://reddit.com/test_post"
    assert formatted["created_utc"].year == 2021
    assert formatted["edited"] is False
    assert formatted["ups"] == 100
    assert formatted["subreddit"] == "testsubreddit"
    assert (
        formatted["permalink"]
        == "/r/testsubreddit/comments/abcdef/test_title/"
    )


def test_get_submission_by_id():
    mock_submission = MagicMock()
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.submission.return_value = mock_submission
        mock_sess.return_value.__enter__.return_value = mock_reddit

        result = mod.get_submission(post_id="submission_id")

        mock_reddit.submission.assert_called_once_with(id="submission_id")
        assert result is mock_submission


def test_get_submission_by_url():
    mock_submission = MagicMock()
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.submission.return_value = mock_submission
        mock_sess.return_value.__enter__.return_value = mock_reddit

        result = mod.get_submission(post_url="submission_url")

        mock_reddit.submission.assert_called_once_with(url="submission_url")
        assert result is mock_submission


def test_get_submission_by_id_exception_logged():
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess, patch(
        "scrapeddit.utils.reddit_utils.logger"
    ) as mock_logger:
        mock_reddit = MagicMock()
        mock_reddit.submission.side_effect = Exception("Test exception")
        mock_sess.return_value.__enter__.return_value = mock_reddit

        result = mod.get_submission(post_id="invalid_id")

        mock_reddit.submission.assert_called_once_with(id="invalid_id")
        mock_logger.error.assert_called_once()
        assert result is None


def test_get_submission_by_url_exception_logged():
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess, patch(
        "scrapeddit.utils.reddit_utils.logger"
    ) as mock_logger:
        mock_reddit = MagicMock()
        mock_reddit.submission.side_effect = Exception("Test exception")
        mock_sess.return_value.__enter__.return_value = mock_reddit

        result = mod.get_submission(post_url="invalid_url")

        mock_reddit.submission.assert_called_once_with(url="invalid_url")
        mock_logger.error.assert_called_once()
        assert result is None


def test_get_submission_no_params():
    with pytest.raises(ValueError):
        mod.get_submission()


def test_get_comment():
    mock_comment = MagicMock()
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.comment.return_value = mock_comment
        mock_sess.return_value.__enter__.return_value = mock_reddit

        result = mod.get_comment(comment_id="comment_url")

        mock_reddit.comment.assert_called_once_with("comment_url")
        assert result is mock_comment


def test_get_comment_exception_logged():
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess, patch(
        "scrapeddit.utils.reddit_utils.logger"
    ) as mock_logger:
        mock_reddit = MagicMock()
        mock_reddit.comment.side_effect = Exception("Test exception")
        mock_sess.return_value.__enter__.return_value = mock_reddit

        result = mod.get_comment(comment_id="invalid_comment_id")

        mock_reddit.comment.assert_called_once_with("invalid_comment_id")
        mock_logger.error.assert_called_once()
        assert result is None


def test_format_comment():
    mock_comment = MagicMock()
    mock_comment.name = "t1_ghijkl"
    mock_comment.author = "comment_user"
    mock_comment.body = "This is a test comment."
    mock_comment.created_utc = 1609459300
    mock_comment.edited = True
    mock_comment.ups = 50
    mock_comment.parent_id = "t3_abcdef"
    mock_comment.link_id = "t3_abcdef"
    mock_comment.subreddit_name_prefixed = "r/testsubreddit"

    formatted = mod.format_comment(mock_comment)

    assert formatted[0] == "t1_ghijkl"
    assert formatted[1] == "comment_user"
    assert formatted[2] == "This is a test comment."
    assert formatted[3].year == 2021
    assert formatted[4] is True
    assert formatted[5] == 50
    assert formatted[6] == "t3_abcdef"
    assert formatted[7] == "t3_abcdef"
    assert formatted[8] == "r/testsubreddit"


def test_format_comment_with_submission_id():
    mock_comment = MagicMock()
    mock_comment.name = "t1_ghijkl"
    mock_comment.author = "comment_user"
    mock_comment.body = "This is a test comment."
    mock_comment.created_utc = 1609459300
    mock_comment.edited = True
    mock_comment.ups = 50
    mock_comment.parent_id = "t3_abcdef"
    mock_comment.link_id = None
    mock_submission = MagicMock()
    mock_submission.id = "submission_id"
    mock_comment.submission = mock_submission
    mock_comment.subreddit_name_prefixed = "r/testsubreddit"

    formatted = mod.format_comment(mock_comment)

    assert formatted[7] == "submission_id"


def test_get_comments_in_thread_by_post_id():
    mock_submission = MagicMock()
    mock_comment1 = MagicMock()
    mock_comment1.name = "t1_comment1"
    mock_comment2 = MagicMock()
    mock_comment2.name = "t1_comment2"
    # construct mock comments list
    mock_submission.comments.list.return_value = [
        mock_comment1,
        mock_comment2,
    ]

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.submission.return_value = mock_submission
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_comments_in_thread(post_id="submission_id")

        mock_reddit.submission.assert_called_once_with(id="submission_id")
        assert comments == [mock_comment1, mock_comment2]


def test_get_comments_in_thread_no_submission():
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.submission.side_effect = Exception("Test exception")
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_comments_in_thread(post_id="invalid_id")

        mock_reddit.submission.assert_called_once_with(id="invalid_id")
        assert comments == []


def test_get_comments_in_thread_exception_logged():
    with patch("scrapeddit.utils.reddit_utils.logger") as mock_logger, patch(
        "scrapeddit.utils.reddit_utils.get_submission"
    ) as mock_get_submission:
        mock_submission = MagicMock()
        mock_comments = MagicMock()
        mock_submission.comments = mock_comments
        mock_comments.replace_more.side_effect = Exception("Test exception")
        mock_get_submission.return_value = mock_submission

        result = mod.get_comments_in_thread(post_id="invalid_id")

        mock_comments.replace_more.assert_called_once()
        mock_logger.error.assert_called_once()
        assert result == []


def test_get_comments_in_thread_by_post_url():
    mock_submission = MagicMock()
    mock_comment1 = MagicMock()
    mock_comment1.name = "t1_comment1"
    mock_comment2 = MagicMock()
    mock_comment2.name = "t1_comment2"
    # construct mock comments list
    mock_submission.comments.list.return_value = [
        mock_comment1,
        mock_comment2,
    ]

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.submission.return_value = mock_submission
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_comments_in_thread(post_url="submission_url")

        mock_reddit.submission.assert_called_once_with(url="submission_url")
        assert comments == [mock_comment1, mock_comment2]


def test_get_redditor_comments():
    mock_redditor = MagicMock()
    mock_comment1 = MagicMock()
    mock_comment1.name = "t1_comment1"
    mock_comment2 = MagicMock()
    mock_comment2.name = "t1_comment2"
    # construct mock comments list
    mock_redditor.comments.new.return_value = [
        mock_comment1,
        mock_comment2,
    ]

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.redditor.return_value = mock_redditor
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_redditors_comments(user_id="test_user", limit=2)

        mock_reddit.redditor.assert_called_once_with("test_user")
        assert comments == [mock_comment1, mock_comment2]


def test_get_redditor_comments_exception_logged():
    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess, patch(
        "scrapeddit.utils.reddit_utils.logger"
    ) as mock_logger:
        mock_reddit = MagicMock()
        mock_reddit.redditor.side_effect = Exception("Test exception")
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_redditors_comments(user_id="invalid_user", limit=2)

        mock_reddit.redditor.assert_called_once_with("invalid_user")
        mock_logger.error.assert_called_once()
        assert comments == []


def test_get_redditor_comments_top():
    mock_redditor = MagicMock()
    mock_comment1 = MagicMock()
    mock_comment1.name = "t1_comment1"
    mock_comment2 = MagicMock()
    mock_comment2.name = "t1_comment2"
    # construct mock comments list
    mock_redditor.comments.top.return_value = [
        mock_comment1,
        mock_comment2,
    ]

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.redditor.return_value = mock_redditor
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_redditors_comments(
            user_id="test_user", limit=2, sort="top"
        )

        mock_reddit.redditor.assert_called_once_with("test_user")
        assert comments == [mock_comment1, mock_comment2]


def test_get_redditor_comments_new():
    mock_redditor = MagicMock()
    mock_comment1 = MagicMock()
    mock_comment1.name = "t1_comment1"
    mock_comment2 = MagicMock()
    mock_comment2.name = "t1_comment2"
    # construct mock comments list
    mock_redditor.comments.new.return_value = [
        mock_comment1,
        mock_comment2,
    ]

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.redditor.return_value = mock_redditor
        mock_sess.return_value.__enter__.return_value = mock_reddit

        comments = mod.get_redditors_comments(
            user_id="test_user", limit=2, sort="new"
        )

        mock_reddit.redditor.assert_called_once_with("test_user")
        assert comments == [mock_comment1, mock_comment2]


def test_get_redditor_comments_invalid_sort():
    mock_redditor = MagicMock()

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:
        mock_reddit = MagicMock()
        mock_reddit.redditor.return_value = mock_redditor
        mock_sess.return_value.__enter__.return_value = mock_reddit

        with pytest.raises(ValueError):
            mod.get_redditors_comments(
                user_id="test_user", limit=2, sort="invalid_sort"
            )

        mock_reddit.redditor.assert_called_once_with("test_user")


def test_get_redditors_from_subreddit():
    mock_subreddit = MagicMock()
    mock_post1 = MagicMock()
    mock_post2 = MagicMock()
    mock_subreddit.new.return_value = [mock_post1, mock_post2]

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess, patch(
        "scrapeddit.utils.reddit_utils.format_submission"
    ) as mock_format:

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_sess.return_value.__enter__.return_value = mock_reddit

        # mock format_submission to return author names
        mock_format.side_effect = [
            {"author": "user1"},
            {"author": "user2"},
        ]

        redditors = mod.get_redditors_from_subreddit(
            subreddit_name="testsubreddit", limit=2, sort="new"
        )

        mock_reddit.subreddit.assert_called_once_with("testsubreddit")
        assert redditors == ["user1", "user2"]


def test_get_redditors_from_subreddit_no_submissions():
    mock_subreddit = MagicMock()
    mock_subreddit.new.return_value = []

    with patch(
        "scrapeddit.utils.connection_utils.reddit_session"
    ) as mock_sess:

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_sess.return_value.__enter__.return_value = mock_reddit

        redditors = mod.get_redditors_from_subreddit(
            subreddit_name="testsubreddit", limit=2, sort="new"
        )

        mock_reddit.subreddit.assert_called_once_with("testsubreddit")
        assert redditors == []
