import praw
from dotenv import load_dotenv, find_dotenv
from asteval import Interpreter
import os
import io

env_path = find_dotenv()
if(not env_path):
    raise Exception("failed to import environment variables, does a .env exist in repo top level?")
load_dotenv(env_path)
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
CLIENT_ID = os.getenv("CLIENT_ID")
# REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_SECRET = os.getenv("SECRET_KEY")
USER_AGENT = os.getenv("USER_AGENT")

#TODO refactor into bot class to scope reddit obj
reddit = praw.Reddit(
    client_id= CLIENT_ID,
    client_secret=CLIENT_SECRET,
    password=PASSWORD,
    user_agent=USER_AGENT,
    username=USERNAME,
)

def post_on_subreddit(subreddit:str, title:str, text:str):
    try:
        reddit.subreddit(subreddit).submit(title, selftext=text)
        print(f"Successfully posted to {subreddit}")
    except Exception as e:
        print(e.__str__())

def get_mentions(new:None | bool = None):
    mentions = reddit.inbox.mentions(limit=None) 
    if new is not None:
        return (m for m in mentions if m.new==new)
    return mentions

def delete_read_mentions():
    read_mentions = get_mentions(False)
    for mention in read_mentions:
        mention.delte()

def reply_to_unread_mentions(callback=lambda _ : "test"):
    unread = get_mentions(True)
    for mention in unread: 
        # print(f"{mention.author}\n{mention.body}")
        reply = mention.reply(callback(mention))
        if(reply is None):
            raise Exception("could not reply")
        mention.mark_read()

def safe_evaluate_comment(comment):
    #TODO return eval errors to commenter
    #TODO format input code to PEP8
    str_buf = io.StringIO()
    aeval = Interpreter(writer=str_buf)
    aeval(comment.body)
    return str_buf.getvalue()

# reply_to_unread_mentions(lambda c: f"you said '{c.body}'")
# reply_to_unread_mentions(safe_evaluate_comment)
