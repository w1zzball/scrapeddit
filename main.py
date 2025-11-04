import praw
from dotenv import load_dotenv, find_dotenv
import os


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
    }


# TODO add logging
class Bot:
    def __init__(
        self, *, username, password, client_id, client_secret, user_agent
    ) -> None:
        self.reddit = praw.Reddit(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

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

comments = bot.get_comments_in_thread("1oohc4a", limit=None)
keys = [
    "name",
    "author",
    "body",
    "created_utc",
    "edited",
    "parent_id",
    "submission",
    "subreddit_name_prefixed",
]
for k in keys:
    print(f"{k}: {getattr(comments[0], k, None)}")
