import requests
import requests.auth
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SECRET_KEY = os.getenv("SECRET_KEY")
USER_AGENT = os.getenv("USER_AGENT")

def get_token():
    client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID,SECRET_KEY)
    post_data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    headers = {"User-Agent": USER_AGENT}
    response = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data, headers=headers)
    token = response.json().get("access_token")
    return token

token = get_token()
headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}


def get_comments_from_subreddit(subreddit, params={"limit": 5, "sort":"new"}):
    url = f"https://oauth.reddit.com/r/{subreddit}/comments"
    response = requests.get(url, headers=headers, params=params)
    return response.json()



srjson = get_comments_from_subreddit("python")
for child in srjson["data"]["children"]:
    print(child["data"]["link_title"]) 
    print(child["data"]["body"])
    print("--"*20)