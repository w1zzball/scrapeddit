import pytest
from unittest.mock import MagicMock, patch
import scrapeddit.utils.reddit_utils as mod


@pytest.fixture(autouse=True)
def mock_with_resources():
    # no-op decorator
    def fake_with_resources(*a, **kw):
        def decorator(func):
            return func

        return decorator

    with pytest.MonkeyPatch.context() as mp:
        import builtins

        mp.setattr(mod, "with_resources", fake_with_resources)
        yield


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
