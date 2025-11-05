import praw
import psycopg
from dotenv import load_dotenv, find_dotenv
import os
from datetime import datetime, timezone
from prompt_toolkit import PromptSession


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
# TODO consider connection pooling with psycopg pool
class Bot:

    def __init__(
        self,
        *,
        username,
        password,
        client_id,
        client_secret,
        user_agent,
        db_string,
    ) -> None:
        # reddit API
        self.reddit = praw.Reddit(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        # db connection
        self.conn = psycopg.connect(db_string)
        self.conn.autocommit = True
        with self.conn.cursor() as cur:
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            print(f"Connected to database, version: {db_version[0]}")

    def get_submission(self, post_id=None, post_url=None) -> praw.models.Submission:
        if post_id:
            submission = self.reddit.submission(post_id)
        elif post_url:
            submission = self.reddit.submission(post_url)
        else:
            raise Exception("provide either a post_id or post_url")
        return submission

    def format_submission(
        self, submission: praw.models.Submission
    ) -> dict[str, str | int | float | bool]:
        formatted_submission = {
            "name": getattr(submission, "name", None),
            "author": format(getattr(submission, "author", None)),
            "title": getattr(submission, "title", None),
            "selftext": getattr(submission, "selftext", None),
            "url": getattr(submission, "url", None),
            "created_utc": datetime.fromtimestamp(
                getattr(submission, "created_utc", 0), tz=timezone.utc
            ),
            "edited": getattr(submission, "edited", None),
            "ups": getattr(submission, "ups", None),
            "subreddit": format(getattr(submission, "subreddit", None)),
            "permalink": format(getattr(submission, "permalink", None)),
        }
        return formatted_submission

    def scrape_submission(self, post_id=None, post_url=None):
        # TODO add overwrite flag
        submission = self.get_submission(post_id, post_url)  # TODO Progress bar
        formatted_submission = self.format_submission(submission)
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO reddit;")
            cur.execute(
                """
                INSERT INTO submissions
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (name) DO NOTHING;
                """,
                list(formatted_submission.values()),
            )
        print(f"Inserted submission with id: {post_id} into database.")

    def get_comment(
        self, comment_id: str
    ) -> praw.models.Comment | praw.models.MoreComments:
        """Get a single comment by its ID."""
        comment = self.reddit.comment(comment_id)
        return comment

    def scrape_comment(self, comment_id: str):
        # TODO add overwrite flag
        comment = self.get_comment(comment_id)
        formatted_comment = self.format_comment(comment)
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO reddit;")
            cur.execute(
                """
                INSERT INTO comments
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (name) DO NOTHING;
                """,
                list(formatted_comment.values()),
            )
        print(f"Inserted comment with id: {comment_id} into database.")

    def get_comments_in_thread(
        self,
        post_id=None,
        post_url=None,
        limit: int | None = 0,
        threshold=0,
    ) -> list[praw.models.Comment | praw.models.MoreComments]:
        """Get all comments in a thread, returns a CommentForest object."""
        submission = self.get_submission(post_id, post_url)
        comments = submission.comments
        comments.replace_more(limit=limit, threshold=threshold)
        return comments.list()

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

    def scrape_comments_in_thread(
        self, post_id=None, post_url=None, limit: int | None = 0, threshold=0
    ):
        # TODO add overwrite flag
        comments = self.get_comments_in_thread(
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

    def scrape_entire_thread(
        self, post_id=None, post_url=None, limit: int | None = 0, threshold=0
    ):
        self.scrape_submission(post_id=post_id, post_url=post_url)
        self.scrape_comments_in_thread(
            post_id=post_id, post_url=post_url, limit=limit, threshold=threshold
        )

    def db_execute(self, sql_str):
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO reddit;")
            cur.execute(sql_str)
            print(cur.fetchone())


def main():
    auth_data = load_auth_data_from_env()
    bot = Bot(**auth_data)
    session = PromptSession()
    while True:
        try:
            user_input = session.prompt("scrapeddit> ")
            if user_input.startswith("scrape "):
                _, post_id_or_url = user_input.split(" ", 1)
                if post_id_or_url.startswith("http"):
                    bot.scrape_entire_thread(post_url=post_id_or_url)
                else:
                    bot.scrape_entire_thread(post_id=post_id_or_url)
            elif user_input.startswith("db "):
                _, sql_str = user_input.split(" ", 1)
                bot.db_execute(sql_str)
            elif user_input in {"exit", "quit"}:
                break
            else:
                print("Unknown command.")
        except KeyboardInterrupt:
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()
