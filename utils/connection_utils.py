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
def db_connection(schema: str | None = "test"):
    conn = psycopg.connect(
        os.getenv("DB_STRING"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema}")
        yield conn
    finally:
        conn.close()


def with_resources(func=None, *, schema: str | None = "test"):
    "decorator for reddit and db connection — can be used as @with_resources or @with_resources()"

    def decorator(f):
        def wrapper(*args, **kwargs):
            with reddit_session() as reddit, db_connection(schema) as conn:
                return f(reddit, conn, *args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    return decorator(func)
