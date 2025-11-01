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

# print(reddit.read_only)


# for submission in reddit.subreddit("test").hot(limit=1):
#     print(dir(submission))

subreddit = reddit.subreddit("test")
title = "Test"
selftext = "Test Content"
subreddit.submit(title, selftext)