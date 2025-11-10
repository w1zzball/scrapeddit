from dotenv import find_dotenv, load_dotenv
import praw
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
        "db_string": os.getenv("DB_STRING"),
    }


reddit = praw.Reddit(**load_auth_data_from_env())

subs = []
for subreddit in reddit.subreddits.popular(limit=1000):
    subs.append((subreddit.display_name, subreddit.subscribers))

# sort by number of subscribers, descending
# subs.sort(key=lambda x: x[1], reverse=True)
subs.sort(key=lambda x: x[1], reverse=False)

subnames = [sub[0] for sub in subs]

with open("top_subreddits.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(subnames))
