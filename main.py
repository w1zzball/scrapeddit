import praw
from dotenv import load_dotenv, find_dotenv
from asteval import Interpreter
import os
import io
load_dotenv(find_dotenv())
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
CLIENT_ID = os.getenv("CLIENT_ID")
# REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_SECRET = os.getenv("SECRET_KEY")
# USER_AGENT = os.getenv("USER_AGENT")

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
        print(f"{mention.author}\n{mention.body}\n")
        reply = mention.reply(callback(mention))
        if(reply is None):
            raise Exception("could not reply")
        mention.mark_read()

def safe_evaluate(code_str):
    str_buf = io.StringIO()
    aeval = Interpreter(writer=str_buf)
    aeval(code_str)
    return str_buf.getvalue()


# reply_to_unread_mentions(lambda c: f"you said '{c.body}'")
# reply_to_unread_mentions(str(eval(c.body)))

# str_buf = io.StringIO()
# aeval = Interpreter(writer=str_buf)
# test = """#adasdas
# print(1)"""
# aeval(test)
# body='''
# #u/bubblebotz
# for i in range(10):
#     print(i, sqrt(i), log(1+1))
# '''
# body2='''
# def f(x):
#     print(x**x)
# f(2)
# '''
# aeval(body2)
m = get_mentions(True)
for n in m:
    print(n.body)
    print(safe_evaluate(n.body))
# aeval_out = str_buf.getvalue()
# print(type(aeval_out))
