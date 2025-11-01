import praw
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_SECRET = os.getenv("SECRET_KEY")
USER_AGENT = os.getenv("USER_AGENT")

reddit = praw.Reddit(
    client_id= CLIENT_ID,
    client_secret=CLIENT_SECRET,
    password=PASSWORD,
    user_agent="Comment Extraction (by u/USERNAME)",
    username=USERNAME,
)

def post_on_subreddit(subreddit:str, title:str, text:str):
    try:
        reddit.subreddit(subreddit).submit(title, selftext=text)
        print(f"Successfully posted to {subreddit}")
    except Exception as e:
        print(e.__str__())

post_on_subreddit("asdajfkje333jjj","test","test")
