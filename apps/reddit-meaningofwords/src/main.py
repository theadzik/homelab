#!/usr/bin/env python

import json
import logging
import os
import re
import unicodedata

import praw
from dotenv import load_dotenv
from openaihelper import WordCheckerResponse
from openaihelper import openai_word_checker


class BotCommenter:
    def __init__(self):
        with open("wordlist.json", mode="r") as file:
            self.words_to_check = json.load(file)
        self.patterns_to_check = {word: r"\b" + word + r"\b" for word in self.words_to_check.keys()}

        self.signature = (
            "🤖 Bip bop, jestem bot. 🤖\n\n"
            "Szukam najczęściej popełnianych błędów w internecie. "
            "[2022](https://nadwyraz.com/blog-raport-100-najczesciej-popelnianych-bledow-w-internecie-w-2022), "
            "[2023](https://nadwyraz.com/blog-raport-50-najczesciej-popelnianych-bledow-w-internecie-w-2023)"
        )
        self.bot_name = os.getenv("REDDIT_USERNAME")

    @staticmethod
    def normalize_comment(body: str) -> str:
        body = body.lower()
        # Remove Polish accents (ł is a special case)
        body = body.replace("ł", "l")
        body = unicodedata.normalize('NFKD', body).encode("ascii", "ignore").decode("ascii")
        return body

    def find_keywords(self, body: str) -> str:
        for word in self.words_to_check:
            if re.search(self.patterns_to_check.get(word), body):
                logging.info(f"Found a comment with {word}!")
                logging.info(REDDIT_BASE_URL + comment.permalink)
                logging.debug(body)
                return word
        return ""

    def parse_reddt_comment(self, content: WordCheckerResponse) -> str:
        message = (
            f"{self.signature}"
            f"\n* Niepoprawna forma: {content.incorrect_word}"
            f"\n* Poprawna forma: {content.correct_word}"
            f"\n* Wyjaśnienie: {content.explanation}"
            f"\n* Poprawione zdanie: {content.corrected_sentence}"
        )
        return message

    def get_extra_info(self, word: str) -> str:
        return " ".join(self.words_to_check.get(word))


load_dotenv()

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    encoding='utf-8',
    level=os.getenv("LOG_LEVEL", logging.INFO)
)

REDDIT_BASE_URL = "https://reddit.com"
SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "polska")

USER_AGENT = f"linux:meaning-of-words:{os.environ.get('APP_VERSION')} (by u/MalinowyChlopak)"

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=USER_AGENT,
)

bot_commenter = BotCommenter()

logging.info("Scanning comments.")
for comment in reddit.subreddit(SUBREDDITS).stream.comments(skip_existing=True):
    normalized_comment = bot_commenter.normalize_comment(comment.body)

    if keyword_found := bot_commenter.find_keywords(body=normalized_comment):
        if comment.author.name == bot_commenter.bot_name:
            logging.info("It's my own comment! Skipping.")
            continue

        extra_info = bot_commenter.get_extra_info(keyword_found)
        content = openai_word_checker(body=comment.body, word=keyword_found, extra_info=extra_info)

        if not content.is_correct:
            logging.info("Phrase used incorrectly. Replying!")
            response = bot_commenter.parse_reddt_comment(content)

            reply_comment = comment.reply(response)
            logging.info(REDDIT_BASE_URL + reply_comment.permalink)
        else:
            logging.info("Phrase used correctly. Skipping.")
            logging.info(content)
