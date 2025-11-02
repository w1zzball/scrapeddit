import praw
from dotenv import load_dotenv, find_dotenv
from asteval import Interpreter
import os
import io


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

    def post_on_subreddit(self, subreddit: str, title: str, text: str):
        try:
            self.reddit.subreddit(subreddit).submit(title, selftext=text)
            print(f"Successfully posted to {subreddit}")
        except Exception as e:
            print(e.__str__())

    def get_mentions(self, new: None | bool = None):
        mentions = self.reddit.inbox.mentions(limit=25)
        if new is not None:
            return (m for m in mentions if m.new == new)
        return mentions

    def delete_read_mentions(self):
        read_mentions = self.get_mentions(False)
        for mention in read_mentions:
            mention.delte()

    def reply_to_unread_mentions(self, callback=lambda _: "test"):
        unread = self.get_mentions(True)
        for mention in unread:
            # print(f"{mention.author}\n{mention.body}")
            reply = mention.reply(callback(mention))
            if reply is None:
                raise Exception("could not reply")
            mention.mark_read()

    def safe_evaluate_comment(self, comment):
        # TODO return eval errors to commenter
        # TODO format input code to PEP8
        str_buf = io.StringIO()
        aeval = Interpreter(writer=str_buf)
        aeval(comment.body)
        return str_buf.getvalue()


auth_data = load_auth_data_from_env()
bot = Bot(**auth_data)

# bot.reply_to_unread_mentions(lambda c: f"you said '{c.body}'")
# bot.reply_to_unread_mentions(safe_evaluate_comment)
for m in bot.reddit.inbox.all():
    print(m)
