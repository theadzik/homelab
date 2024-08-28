#!/usr/bin/env python

import json
import logging
import os

import praw
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

USER_AGENT = "linux:meaning-of-words:2024.08.1 (by u/MalinowyChlopak)"

CLIENT_ID = os.environ.get("CLIENT_ID", None)
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", None)
USERNAME = os.environ.get("USERNAME", None)
PASSWORD = os.environ.get("PASSWORD", None)

with open("dictionary.json", mode="r") as file:
    dictionary = json.load(file)

words_to_check = [word for word in dictionary.keys()]

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=USERNAME,
    password=PASSWORD,
    user_agent=USER_AGENT,
)

for comment in reddit.subreddit("all").stream.comments():
    normalized_comment = comment.body.lower()

    logging.debug(f"Checking comment {comment.id}")
    for word in words_to_check:
        if word in normalized_comment:
            logging.info(comment.permalink)
            logging.info(normalized_comment)

# Got prawcore.exceptions.TooManyRequests
