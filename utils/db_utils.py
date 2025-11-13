from .console import console
from .connection_utils import with_resources

"""
    Utils for purely database operations
"""


@with_resources(use_db=True, use_reddit=False)
def db_execute(conn, sql_str):
    with conn.cursor() as cur:
        try:
            cur.execute(sql_str)
            # If the statement returned rows, fetch and print them.
            # Otherwise print how many rows were affected.
            if cur.description is not None:
                rows = cur.fetchall()
                console.print(rows)
            else:
                console.print(f"Query OK, {cur.rowcount} rows affected.")
        except Exception as e:
            # Print a concise psycopg error message instead of
            # the full traceback.
            ename = f"{e.__class__.__module__}.{e.__class__.__name__}"
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
            comments_deleted = cur.rowcount
        if target in ("submissions", "all"):
            cur.execute("DELETE FROM submissions;")
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
    return redditors
