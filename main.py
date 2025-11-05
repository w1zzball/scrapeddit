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
# TODO skip scraped thread
# TODO insert OP
# TODO consider connection pooling with psycopg pool
class Bot:
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
        # TODO look into autocommit
        self.conn = psycopg.connect(db_string)
        self.conn.autocommit = True
        with self.conn.cursor() as cur:
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            print(f"Connected to database, version: {db_version[0]}")

    def scrape_thread_comments(
        self, post_id=None, post_url=None, limit: int | None = 0, threshold=0
    ):
        comments = bot.get_comments_in_thread(
            post_id=post_id, post_url=post_url, limit=limit, threshold=threshold
        )
        formatted_comments = map(self.format_comment, comments)  # TODO Progress bar
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO reddit;")
            for formatted_comment in formatted_comments:
                cur.execute(
                    """
                INSERT INTO comments
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (name) DO NOTHING;
                """,
                    list(formatted_comment.values()),
                )
        print(f"Inserted {len(comments)} comments from thread {post_id} into database.")

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

    def format_comment(
        self, comment: praw.models.Comment
    ) -> dict[str, str | int | float | bool]:
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
            "subreddit_name_prefixed": getattr(
                comment, "subreddit_name_prefixed", None
            ),
        }
        return formatted_comment


auth_data = load_auth_data_from_env()
bot = Bot(**auth_data)

# comments = bot.get_comments_in_thread("1oohc4a", limit=None)

# thread with deleted comments
# TODO factor into bot class
# comments = bot.get_comments_in_thread("1om49zc", limit=None)
bot.scrape_thread_comments("1oohc4a")
