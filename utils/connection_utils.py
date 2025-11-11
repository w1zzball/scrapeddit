import praw
import psycopg
import os
from contextlib import contextmanager


@contextmanager
def reddit_session():
    reddit = praw.Reddit(
        username=os.getenv("USERNAME"),
        password=os.getenv("PASSWORD"),
        client_id=os.getenv("CLIENT_ID"),
        # REDIRECT_URI = os.getenv("REDIRECT_URI")
        client_secret=os.getenv("SECRET_KEY"),
        user_agent=os.getenv("USER_AGENT"),
    )
    try:
        yield reddit
    finally:
        del reddit


@contextmanager
def db_connection(schema: str | None = "test", auto_commit: bool = True):
    conn = psycopg.connect(
        os.getenv("DB_STRING"),
        autocommit=auto_commit,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema}")
        yield conn
    finally:
        conn.close()


def with_resources(use_db=True, use_reddit=True, *, schema: str | None = "test"):
    """Decorator for optional reddit and db resources."""

    def decorator(f):
        def wrapper(*args, **kwargs):
            if use_reddit and use_db:
                with reddit_session() as reddit, db_connection(schema) as conn:
                    return f(reddit, conn, *args, **kwargs)
            elif use_reddit:
                with reddit_session() as reddit:
                    return f(reddit, *args, **kwargs)
            elif use_db:
                with db_connection(schema) as conn:
                    return f(conn, *args, **kwargs)
            else:
                return f(*args, **kwargs)

        return wrapper

    return decorator
