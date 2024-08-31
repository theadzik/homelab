#!/usr/bin/env python

import json
import logging
import os
import re
import unicodedata

import nltk
import praw
from dotenv import load_dotenv
from graceful_shutdown import GracefulKiller
from openaihelper import OpenAIChecker
from openaihelper import WordCheckerResponse


class BotCommenter:
    def __init__(self):
        with open(os.getenv("REDDIT_DICTIONARY_PATH"), mode="r", encoding="utf-8") as file:
            self.words_to_check = json.load(file)
        self.patterns_to_check = {word: value.get("search_rule") for word, value in self.words_to_check.items()}
        logging.info(f"Loaded {len(self.words_to_check)} rules.")
        self.signature = (
            "🤖 Bip bop, jestem bot. 🤖\n\n"
            "Szukam najczęściej popełnianych błędów w internecie: "
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

    def find_keywords(self, body: str) -> (str, str):
        for word in self.patterns_to_check.keys():
            if match := re.search(self.patterns_to_check.get(word), body):
                logging.info(f"Found a comment with {word}!")
                logging.info(REDDIT_BASE_URL + comment.permalink)
                logging.debug(body)
                return word, match.group(0)
        return "", ""

    @staticmethod
    def get_sentence_indexes(word: str, body: str, limit: int = 0) -> (int, int):
        """Finds a 'word' in 'body' and returns the first sentence with the 'word'.
        By default, only the sentence with the word is returned.
        When the limit is >0, the sentence is returned with additional sentences before and after it.
        """
        sentences = nltk.tokenize.sent_tokenize(body, language="polish")
        num_of_sentences = len(sentences)
        for index, sentence in enumerate(sentences):
            if word in sentence:
                start_index = max(0, index - limit)
                end_index = min(num_of_sentences, index + limit + 1)
                logging.info(f"Calculated start and end indexes of sentences [{start_index}:{end_index}]")
                return start_index, end_index

    @staticmethod
    def get_sentences(body: str, start_index: int, end_index: int) -> str:
        """We assume that sent_tokenize will always return the same indexes for
        normalized and non-normalized text.
        """
        sentences = nltk.tokenize.sent_tokenize(body, language="polish")
        return " ".join(sentences[start_index:end_index])

    def parse_reddt_comment(self, content: WordCheckerResponse) -> str:
        message = (
            f"{self.signature}"
            f"\n* Niepoprawna forma: {content.incorrect_word}"
            f"\n* Poprawna forma: {content.correct_word}"
            f"\n* Wyjaśnienie: {content.explanation}"
        )
        return message

    def get_extra_info(self, word: str) -> str:
        return " ".join(self.words_to_check.get(word).get("explanations"))


load_dotenv()

nltk.download('punkt_tab', download_dir="/nltk_data")

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
openai_checker = OpenAIChecker()
killer = GracefulKiller()

logging.info("Scanning comments.")
for comment in reddit.subreddit(SUBREDDITS).stream.comments(skip_existing=True):
    if killer.kill_now:
        break
    normalized_comment = bot_commenter.normalize_comment(comment.body)

    keyword_found, match = bot_commenter.find_keywords(body=normalized_comment)
    if keyword_found:
        if comment.author.name == bot_commenter.bot_name:
            logging.info("It's my own comment! Skipping.")
            continue

        extra_info = bot_commenter.get_extra_info(keyword_found)
        start_index, end_index = bot_commenter.get_sentence_indexes(word=match, body=normalized_comment, limit=1)
        limited_body = bot_commenter.get_sentences(body=comment.body, start_index=start_index, end_index=end_index)

        content = openai_checker.get_explanation(body=limited_body, word=keyword_found, extra_info=extra_info)

        if not content.is_correct:
            logging.info("Phrase used incorrectly. Replying!")
            response = bot_commenter.parse_reddt_comment(content)
            reply_comment = comment.reply(response)
            logging.info(REDDIT_BASE_URL + reply_comment.permalink)
        else:
            logging.info("Phrase used correctly. Skipping.")
            logging.info(content)

logging.info("Received kill signal. Shutting down.")
