#!/usr/bin/env python

import json
import logging
import os
import unicodedata

import praw
from dotenv import load_dotenv
from openaihelper import openai_word_checker


class BotCommenter:
    def __init__(self):
        with open("wordlist.json", mode="r") as file:
            self.words_to_check = json.load(file)

        self.signature = "Bip bop, jestem bot. Wybacz jeśli się pomyliłem."
        self.bot_name = "MeaningOfWordsBot"

    @staticmethod
    def normalize_comment(body: str) -> str:
        body = body.lower()
        # Remove Polish accents (ł is a special case)
        body = body.replace("ł", "l")
        body = unicodedata.normalize('NFKD', body).encode("ascii", "ignore").decode("ascii")
        return body

    def find_keywords(self, body: str) -> str:
        for word in self.words_to_check:
            if word in body:
                logging.info(f"Found a comment with {word}!")
                logging.info(comment.permalink)
                logging.debug(body)
                return word
        return ""


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("meaningofwords.log", "a", "utf-8"),
        logging.StreamHandler()
    ],
    format="%(asctime)s %(levelname)s %(msg)s"
)

USER_AGENT = "linux:meaning-of-words:2024.08.1 (by u/MalinowyChlopak)"

CLIENT_ID = os.environ.get("CLIENT_ID", None)
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", None)
USERNAME = os.environ.get("USERNAME", None)
PASSWORD = os.environ.get("PASSWORD", None)
SUBREDDIT = os.environ.get("SUBREDDIT", "all")

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=USERNAME,
    password=PASSWORD,
    user_agent=USER_AGENT,
)

bot_commenter = BotCommenter()

for comment in reddit.subreddit(SUBREDDIT).stream.comments(skip_existing=True):
    normalized_comment = bot_commenter.normalize_comment(comment.body)

    if keyword_found := bot_commenter.find_keywords(body=normalized_comment):
        if comment.author.name == bot_commenter.bot_name:
            logging.info("It's my own comment! Not Replying!")
            continue
        if response := openai_word_checker(body=comment.body, word=keyword_found):
            logging.info("Replying.")
            response += f"\n\n{bot_commenter.signature}"
            reply_comment = comment.reply(response)
            logging.info(reply_comment.permalink)
        else:
            logging.info("Not replying.")
            continue
