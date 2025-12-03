import logging
from .console import console
from .connection_utils import with_resources

"""
    Utils for purely database operations
"""

logger = logging.getLogger(__name__)


@with_resources(use_db=True, use_reddit=False)
def db_execute(conn, sql_str):
    with conn.cursor() as cur:
        try:
            cur.execute(sql_str)
            logger.info("Executed SQL: %s", sql_str)
            if cur.description is not None:
                rows = cur.fetchall()
                console.print(rows)
            else:
                console.print(f"Query OK, {cur.rowcount} rows affected.")
        except Exception as e:
            # get psycopg error rather than traceback
            ename = f"{e.__class__.__module__}.{e.__class__.__name__}"
            logger.error("SQL execution error: %s: %s", ename, e)
            console.print(f"{ename}: {e}")


@with_resources(use_db=True, use_reddit=False)
def clear_tables(conn, target: str = "all") -> tuple[int, int]:
    """Delete rows from comments and/or submissions.

    target: 'comments', 'submissions', or 'all'. Returns a tuple of
    deleted counts (submissions_deleted, comments_deleted).
    This does NOT drop tables—only deletes rows.
    """
    submissions_deleted = 0
    comments_deleted = 0
    with conn.cursor() as cur:
        if target in ("comments", "all"):
            cur.execute("DELETE FROM comments;")
            logger.info("Deleted %d rows from comments", cur.rowcount)
            comments_deleted = cur.rowcount
        if target in ("submissions", "all"):
            cur.execute("DELETE FROM submissions;")
            logger.info("Deleted %d rows from submissions", cur.rowcount)
            submissions_deleted = cur.rowcount
    return submissions_deleted, comments_deleted


@with_resources(use_db=True, use_reddit=False)
def db_get_redditors_from_subreddit(
    conn, subreddit: str, limit: int = 100
) -> list[str]:
    """Given a subreddit fetch all redditors with comments on that subreddit"""
    subreddit_name = (
        subreddit if subreddit.startswith("r/") else "r/" + subreddit
    )
    with conn.cursor() as cur:
        cur.execute(
            f"""
                    SELECT DISTINCT author FROM comments
                    WHERE subreddit = '{subreddit_name}'
                    LIMIT {limit};
        """
        )
        res = cur.fetchall()
    redditors = [row[0] for row in res]
    logger.info(
        "Fetched %d redditors from subreddit %s",
        len(redditors),
        subreddit_name,
    )
    return redditors


@with_resources(use_db=True, use_reddit=False)
def insert_submission(conn, submission, overwrite=False):
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
    logger.info("loading submission data into DB...")
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
        return res
