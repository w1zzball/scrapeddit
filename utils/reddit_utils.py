from datetime import datetime, timezone
import logging
from typing import Any
from .connection_utils import with_resources
from .console import console

"""Utils for pure Reddit operations."""

logger = logging.getLogger(__name__)


def format_submission(submission: Any) -> dict[str, str | int | float | bool]:
    formatted_submission = {
        "name": getattr(submission, "name", None),
        "author": format(getattr(submission, "author", None)),
        "title": getattr(submission, "title", None),
        "selftext": getattr(submission, "selftext", None),
        "url": getattr(submission, "url", None),
        "created_utc": datetime.fromtimestamp(
            getattr(submission, "created_utc", 0), tz=timezone.utc
        ),
        "edited": bool(getattr(submission, "edited", None)),
        "ups": getattr(submission, "ups", None),
        "subreddit": format(getattr(submission, "subreddit", None)),
        "permalink": format(getattr(submission, "permalink", None)),
    }
    return formatted_submission


@with_resources(use_reddit=True, use_db=False)
def get_submission(reddit, post_id=None, post_url=None):
    if post_id:
        try:
            submission = reddit.submission(id=post_id)
        except Exception as e:
            logger.error("Error fetching submission by ID %s: %s", post_id, e)
            return None
    elif post_url:
        try:
            submission = reddit.submission(url=post_url)
        except Exception as e:
            logger.error(
                "Error fetching submission by URL %s: %s", post_url, e
            )
            return None
    else:
        raise ValueError("Either post_id or post_url must be provided.")
    return submission


@with_resources(use_reddit=True, use_db=False)
def get_comment(reddit, comment_id: str) -> Any:
    """
    Get a single comment by its ID.
    """
    try:
        comment = reddit.comment(comment_id)
    except Exception as e:
        logger.error("Error fetching comment by ID %s: %s", comment_id, e)
        return None
    return comment


def format_comment(comment: Any) -> tuple:
    formatted_comment = (
        getattr(comment, "name", None),
        format(getattr(comment, "author", None)),
        getattr(comment, "body", None),
        datetime.fromtimestamp(
            getattr(comment, "created_utc", 0),
            tz=timezone.utc,
        ),
        bool(getattr(comment, "edited", None)),
        getattr(comment, "ups", None),
        getattr(comment, "parent_id", None),
        (
            getattr(comment, "link_id", None)
            or getattr(getattr(comment, "submission", None), "id", None)
            or format(getattr(comment, "submission", None))
        ),
        getattr(comment, "subreddit_name_prefixed", None),
    )
    return formatted_comment


def get_comments_in_thread(
    post_id=None,
    post_url=None,
    limit: int | None = None,
    threshold=0,
) -> list[Any]:
    """Get all comments in a thread, returns a CommentForest object."""
    try:
        submission = get_submission(post_id, post_url)
    except Exception as e:
        logger.error("Error fetching submission: %s", e)
        return []
    comments = submission.comments
    # with console.status("Fetching comments...", spinner="dots"):
    try:
        comments.replace_more(limit=limit, threshold=threshold)
    except Exception as e:
        logger.error("Error replacing more comments: %s", e)
        return []
    return comments.list()


@with_resources(use_reddit=True, use_db=False)
def get_redditors_comments(
    reddit, user_id: str, limit: int = 100, sort: str = "new"
) -> list[Any]:
    """
    Get all comments made by a specific user.
    """
    try:
        redditor = reddit.redditor(user_id)
    except Exception as e:
        logger.error("Error fetching redditor by ID %s: %s", user_id, e)
        return []
    if sort == "new":
        try:
            return redditor.comments.new(limit=limit)
        except Exception as e:
            logger.error(
                "Error fetching new comments for redditor %s: %s", user_id, e
            )
            return []
    elif sort == "top":
        try:
            return redditor.comments.top(limit=limit)
        except Exception as e:
            logger.error(
                "Error fetching top comments for redditor %s: %s", user_id, e
            )
            return []
    else:
        logger.error("Get redditor comments- unknown sort order: %s", sort)
        raise ValueError(f"Unknown sort order: {sort}")


@with_resources(use_db=False, use_reddit=True)
def get_redditors_from_subreddit(
    reddit, subreddit_name: str, limit: int = 100, sort: str = "new"
):
    """Given a subreddit fetch redditors with comments on that subreddit"""
    try:
        sub = reddit.subreddit(subreddit_name)
    except Exception as e:
        logger.error("Error fetching subreddit %s: %s", subreddit_name, e)
        return []
    sorter = sort.lower()
    fetchers = {
        "new": sub.new,
        "hot": sub.hot,
        "top": sub.top,
        "rising": sub.rising,
        "controversial": sub.controversial,
    }
    try:
        iterator = fetchers.get(sorter, sub.new)(limit=limit)
    except Exception as e:
        logger.error(
            "Error fetching submissions from subreddit %s: %s",
            subreddit_name,
            e,
        )
        return []
    submissions = list(iterator)
    if not submissions:
        console.print("No submissions found.")
        return []
    redditors = [format_submission(s)["author"] for s in submissions]
    return redditors
