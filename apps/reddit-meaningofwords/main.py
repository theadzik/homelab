#!/usr/bin/env python

import datetime
import json
import logging
import os

import praw
import prawcore
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

counter = 0
start_time = datetime.datetime.now()
try:
    for comment in reddit.subreddit("all").stream.comments(skip_existing=True):
        counter += 1
        normalized_comment = comment.body.lower()

        current_time = datetime.datetime.now()
        current_seconds = (current_time - start_time).total_seconds()
        logging.info(f"Total counter: {counter} at rate: {(counter/current_seconds):.2f} req/s")
        for word in words_to_check:
            if word in normalized_comment:
                logging.warning(comment.permalink)
                logging.warning(normalized_comment)
except prawcore.exceptions.TooManyRequests:
    end_time = datetime.datetime.now()
    end_seconds = (end_time-start_time).total_seconds()
    logging.error(f"TooManyRequests: {counter} iterations over {end_seconds}s, {(counter/end_seconds):.2f}req/s")
