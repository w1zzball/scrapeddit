from .io_utils import console
from .reddit_utils import (
    get_submission,
    format_submission,
    get_comment,
    format_comment,
)
from .connection_utils import with_resources


# TODO factor out insertion into separate db_utils.py
@with_resources(use_reddit=False, use_db=True)
def scrape_submission(
    conn,
    post_id: str | None = None,
    post_url: str | None = None,
    overwrite: bool = False,
    index=None,
    total: int | None = None,
):
    """Fetch a submission and insert it into the DB.

    If overwrite is True, existing rows will be updated on conflict.
    """
    submission = get_submission(post_id, post_url)
    submission = format_submission(submission)
    cols = (
        "(name, author, title, selftext, url, created_utc, "
        "edited, ups, subreddit, permalink)"
    )
    placeholders = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s"
    if overwrite:
        conflict_clause = (
            "ON CONFLICT (name) DO UPDATE SET "
            "author=EXCLUDED.author, "
            "title=EXCLUDED.title, "
            "selftext=EXCLUDED.selftext, "
            "url=EXCLUDED.url, "
            "created_utc=EXCLUDED.created_utc, "
            "edited=EXCLUDED.edited, "
            "ups=EXCLUDED.ups, "
            "subreddit=EXCLUDED.subreddit, "
            "permalink=EXCLUDED.permalink "
            "RETURNING name;"
        )
    else:
        conflict_clause = "ON CONFLICT (name) DO NOTHING RETURNING name;"

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO submissions {cols}
            VALUES ({placeholders})
            {conflict_clause}
            """,
            list(submission.values()),
        )
        res = cur.fetchone()
    if res:
        prefix = ""
        if index is not None and total is not None:
            prefix = f"[{index}/{total}] "
        elif index is not None:
            prefix = f"[{index}] "
        console.print(f"{prefix}Inserted/updated submission {res[0]}")
    else:
        console.print("No change to submission (conflict and skipped)")


@with_resources(use_reddit=False, use_db=True)
def scrape_comment(conn, comment_id: str, overwrite: bool = False):
    """
    Fetch a single comment and insert into DB.

    If overwrite=True update on conflict.
    """
    comment = get_comment(comment_id)
    formatted_comment = format_comment(comment)
    cols = (
        "(name, author, body, created_utc, edited, ups, "
        "parent_id, submission_id, subreddit)"
    )
    placeholders = "%s,%s,%s,%s,%s,%s,%s,%s,%s"
    if overwrite:
        conflict_clause = (
            "ON CONFLICT (name) DO UPDATE SET "
            "author=EXCLUDED.author, body=EXCLUDED.body, "
            "created_utc=EXCLUDED.created_utc, edited=EXCLUDED.edited, "
            "ups=EXCLUDED.ups, parent_id=EXCLUDED.parent_id, "
            "submission_id=EXCLUDED.submission_id, "
            "subreddit=EXCLUDED.subreddit RETURNING name;"
        )
    else:
        conflict_clause = "ON CONFLICT (name) DO NOTHING RETURNING name;"

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO comments {cols}
            VALUES ({placeholders})
            {conflict_clause}
            """,
            formatted_comment,
        )
        res = cur.fetchone()
    if res:
        console.print(f"Inserted/updated comment {res[0]}")
    else:
        console.print("No change to comment (conflict and skipped)")
