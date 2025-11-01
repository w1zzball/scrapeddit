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

client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID,SECRET_KEY)
post_data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
headers = {"User-Agent": "bubblebotz/0.1 by bubblebotz"}
response = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data, headers=headers)
print(response.json())