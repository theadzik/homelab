#!/usr/bin/env python

import datetime
import json
import logging
import os

import praw
import prawcore
from dotenv import load_dotenv


class CommentValidator:
    def __init__(self):
        with open("dictionary.json", mode="r") as file:
            self.dictionary = json.load(file)

        self.words_to_check = [word for word in self.dictionary.keys()]

    @staticmethod
    def normalize_comment(body: str) -> str:
        return body.lower()

    def should_comment(self, body: str, word: str) -> bool:
        ignore_list = self.dictionary.get(word).get("ignore")
        for ignore_word in ignore_list:
            if ignore_word in body:
                logging.info(f"Ignoring comment! It has \"{ignore_word}\" in it.")
                return False
        logging.info("No ignored words found.")
        return True

    def find_keywords(self, body: str) -> str:
        for word in self.words_to_check:
            if word in body:
                logging.info("Found a comment!")
                logging.info(comment.permalink)
                logging.info(body)
                return word
        return ""


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("meaningofwords.log"),
        logging.StreamHandler()
    ],
    format="%(asctime)s %(levelname)s %(msg)s"
)

USER_AGENT = "linux:meaning-of-words:2024.08.1 (by u/MalinowyChlopak)"

CLIENT_ID = os.environ.get("CLIENT_ID", None)
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", None)
USERNAME = os.environ.get("USERNAME", None)
PASSWORD = os.environ.get("PASSWORD", None)

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=USERNAME,
    password=PASSWORD,
    user_agent=USER_AGENT,
)

comment_validator = CommentValidator()

counter = 0
start_time = datetime.datetime.now()
try:
    for comment in reddit.subreddit("test").stream.comments(skip_existing=True):
        counter += 1
        normalized_comment = comment_validator.normalize_comment(comment.body)

        current_time = datetime.datetime.now()
        current_seconds = (current_time - start_time).total_seconds()
        logging.debug(f"Total counter: {counter} at rate: {(counter / current_seconds):.2f} req/s")
        if keyword_found := comment_validator.find_keywords(body=normalized_comment):
            if comment_validator.should_comment(body=normalized_comment, word=keyword_found):
                logging.info("Commenting!")
            else:
                logging.info("Ignoring.")
except prawcore.exceptions.TooManyRequests:
    end_time = datetime.datetime.now()
    end_seconds = (end_time - start_time).total_seconds()
    logging.error(f"TooManyRequests: {counter} iterations over {end_seconds}s, {(counter / end_seconds):.2f}req/s.")
