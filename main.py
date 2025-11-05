import praw
import psycopg
from dotenv import load_dotenv, find_dotenv
import os
from datetime import datetime, timezone


def load_auth_data_from_env() -> dict[str, str | None]:
    env_path = find_dotenv()
    if not env_path:
        raise Exception(
            "failed to import environment variables,"
            " does a .env exist in repo top level?"
        )
    load_dotenv(env_path, override=True)

    return {
        "username": os.getenv("USERNAME"),
        "password": os.getenv("PASSWORD"),
        "client_id": os.getenv("CLIENT_ID"),
        # REDIRECT_URI = os.getenv("REDIRECT_URI")
        "client_secret": os.getenv("SECRET_KEY"),
        "user_agent": os.getenv("USER_AGENT"),
        "db_string": os.getenv("DB_STRING"),
    }


# TODO add logging
class Bot:
    def __init__(
        self, *, username, password, client_id, client_secret, user_agent, db_string
    ) -> None:
        self.reddit = praw.Reddit(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        # db connection
        self.conn = psycopg.connect(db_string)
        with self.conn.cursor() as cur:
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            print(f"Connected to database, version: {db_version[0]}")

    def scrape_thread(
        self, post_id=None, post_url=None, limit: int | None = 0, threshold=0
    ):
        pass

    def db_execute(self, sql_str):
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO reddit;")
            cur.execute(sql_str)
            print(cur.fetchone())

    # def write_to_db(self, formatted_comment):
    #     with self.conn.cursor() as cur:
    #         cur

    def get_top_level_comments_in_thread(
        self, post_id=None, post_url=None, limit: int | None = 0, threshold=0
    ):
        if post_id:
            top_level_comments = self.reddit.submission(post_id).comments
        elif post_url:
            top_level_comments = self.reddit.submission(post_url).comments
        else:
            raise Exception("provide either a post_id or post_url")
        top_level_comments.replace_more(limit=limit, threshold=threshold)
        for top_level_comment in top_level_comments:
            print(top_level_comment.body)

    def get_comments_in_thread(
        self,
        post_id=None,
        post_url=None,
        limit: int | None = 0,
        threshold=0,
    ) -> list[praw.models.Comment | praw.models.MoreComments]:
        """Get all comments in a thread, returns a CommentForest object."""
        if post_id:
            comments = self.reddit.submission(post_id).comments
        elif post_url:
            comments = self.reddit.submission(post_url).comments
        else:
            raise Exception("provide either a post_id or post_url")
        comments.replace_more(limit=limit, threshold=threshold)
        return comments.list()
        # for comment in comments.list():
        #     return comment.body


auth_data = load_auth_data_from_env()
bot = Bot(**auth_data)

# comments = bot.get_comments_in_thread("1oohc4a", limit=None)

# thread with deleted comments
comments = bot.get_comments_in_thread("1om49zc", limit=None)

keys = [
    "name",
    "author",
    "body",
    "created_utc",
    "edited",
    "ups",
    "parent_id",
    "submission",
    "subreddit_name_prefixed",
]


def format_comment(comment: praw.models.Comment) -> dict[str, str | int | float | bool]:
    formatted_comment = {
        "name": getattr(comment, "name", None),
        "author": format(getattr(comment, "author", None)),
        "body": getattr(comment, "body", None),
        "created_utc": datetime.fromtimestamp(
            getattr(comment, "created_utc", 0), tz=timezone.utc
        ),
        "edited": getattr(comment, "edited", None),
        "ups": getattr(comment, "ups", None),
        "parent_id": getattr(comment, "parent_id", None),
        "submission": format(getattr(comment, "submission", None)),
        "subreddit_name_prefixed": getattr(comment, "subreddit_name_prefixed", None),
    }
    return formatted_comment


# for k in keys:
#     print(f"{k}: {getattr(comments[0], k, None)}")

# bot.db_execute("SELECT * FROM comment;")

# print(format_comment(comments[0]))

formatted_comment = format_comment(comments[0])
# print(formatted_comment.values())
values = str(list(formatted_comment.values()))[1:-1]
sql_str = f"INSERT INTO comments VALUES ({values}); "
# print(sql_str)
bot.db_execute("SELECT * FROM comments")
# bot.db_execute(sql_str)
cur = bot.conn.cursor()
cur.execute("SET search_path TO reddit;")
cur.execute(
    """
    INSERT INTO comments
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    list(formatted_comment.values()),
)
bot.conn.commit()
cur.close()
