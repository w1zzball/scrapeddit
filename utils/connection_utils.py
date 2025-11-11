from re import L
import praw
import psycopg
import os
from contextlib import contextmanager
from dotenv import load_dotenv

@contextmanager
def reddit_session():
    reddit = praw.Reddit(
        username= os.getenv("USERNAME"),
        password= os.getenv("PASSWORD"),
        client_id= os.getenv("CLIENT_ID"),
        # REDIRECT_URI = os.getenv("REDIRECT_URI")
        client_secret= os.getenv("SECRET_KEY"),
        user_agent= os.getenv("USER_AGENT"),
        )
    try:
        yield reddit
    finally:
        del reddit

@contextmanager
def db_connection():
    conn = psycopg.connect(
        db_string: os.getenv("DB_STRING"),
    )
    try:
        yield conn
    finally:
        conn.close()


def with_resources():
    "decorator for reddit and bd connection"
    def decorator(func):
        def wrapper(*args,**kwargs):
            with reddit_session() as reddit, db_connection() as conn:
                return func(reddit,conn,*args,**kwargs)
        return wrapper
    return decorator
