import praw
import psycopg
from psycopg import sql
import os
from contextlib import contextmanager
from typing import Generator, Callable, Any, TypeVar
import logging

logger = logging.getLogger(__name__)


@contextmanager
def reddit_session() -> Generator[praw.Reddit, None, None]:
    """provide a reddit instance"""
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
    except Exception as e:
        logger.error("Reddit session error: %s", e)
        raise (e)
    finally:
        del reddit


@contextmanager
def db_connection(
    schema: str = "test", auto_commit: bool = True
) -> Generator[psycopg.Connection, None, None]:
    """provide a database connection"""
    db_string = os.getenv("DB_STRING") or "localhost"
    conn = psycopg.connect(
        db_string,
        autocommit=auto_commit,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
            )
        yield conn
    except Exception as e:
        logger.error("Database connection error: %s", e)
    finally:
        conn.close()


def with_resources(
    use_db: bool = True,
    use_reddit: bool = True,
    *,
    schema: str = "test",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for optional reddit and db resources."""
    # typing to prevent type checker complaints on wrapped functions
    T = TypeVar("T", bound=Callable[..., Any])

    def decorator(f: T) -> T:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
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

        return wrapper  # type: ignore[return-value]

    return decorator
