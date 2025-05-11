import json
import os
import random
import re
import time

import praw
from custom_logger import get_logger
from database import DatabaseClientSingleton
from openai_helper import WordCheckerResponse

logger = get_logger(__name__)


class BotCommenter:
    def __init__(self):
        with open(
            os.environ["REDDIT_SIGNATURE_PATH"], mode="r", encoding="utf-8"
        ) as file:
            self.signature = file.read().strip()
            logger.debug(f"Loaded signature:\n{self.signature}")
        with open(
            os.environ["REDDIT_DICTIONARY_PATH"], mode="r", encoding="utf-8"
        ) as file:
            self.words_to_check = json.load(file)

        self.patterns_to_check = {
            word: value.get("search_rule")
            for word, value in self.words_to_check.items()
        }
        logger.debug(f"Loaded {len(self.words_to_check)} rules.")
        self.bot_name = os.environ["REDDIT_USERNAME"]
        self.REDDIT_BASE_URL = "https://reddit.com"

    def find_keywords(self, body: str, skip_citations: bool = True) -> (str, str):
        database_client = DatabaseClientSingleton()
        words = database_client.get_sorted_words()

        for word in words:
            logger.debug(f"Looking for {word}")

            if skip_citations:
                pattern = self.get_skip_citation_pattern(
                    self.patterns_to_check.get(word)
                )
                match_group = 1
            else:
                pattern = self.patterns_to_check.get(word)
                match_group = 0

            if match := re.search(pattern, body, flags=re.IGNORECASE | re.MULTILINE):
                logger.debug(f"Found a comment with {word}!")
                logger.debug(body)
                logger.debug(match)
                logger.debug(match.group(match_group))

                return word, match.group(match_group)
        return "", ""

    @staticmethod
    def get_skip_citation_pattern(original_pattern: str) -> str:
        skip_citations_pattern = r"^(?! *?>)(?:.*?)("
        pattern = f"{skip_citations_pattern}{original_pattern})"
        return pattern

    def parse_reddit_explanation(
        self, content: WordCheckerResponse, sources: str
    ) -> str:
        # Add two spaces in front of the new paragraph to continue under the same bullet point.
        explanation = content.explanation.replace("\n\n", "\n\n  ")

        message = (
            f"{self.signature}"
            f"\n* Użyta forma: {content.used_word}"
            f"\n* Poprawna forma: **{content.correct_word}**"
            f"\n* Wyjaśnienie: {explanation}"
            f"\n* Źródła: {sources}"
        )
        return message

    def parse_reddit_sources(self, word: str) -> str:
        markdown_links = []
        links = self.words_to_check.get(word).get("sources")
        for idx, source in enumerate(links):
            markdown_links.append(f"[{idx + 1}]({source})")

        return ", ".join(markdown_links)

    def get_extra_info(self, word: str) -> str:
        return " ".join(self.words_to_check.get(word).get("explanations"))

    def is_my_comment_chain(
        self, comment: praw.models.Comment, direct: bool = False
    ) -> bool:
        ancestor = comment
        refresh_counter = 0
        while not ancestor.is_root:
            if direct and refresh_counter > 0:
                return False
            ancestor = ancestor.parent()
            if ancestor.author == self.bot_name:
                return True
            if refresh_counter % 9 == 0:
                ancestor.refresh()
            refresh_counter += 1
        return False

    def is_bad_bot_comment(self, comment: praw.models.Comment) -> bool:
        bad_bot_strings = ["bad bot", "badbot", "zły bot", "zly bot"]
        if any(
            bad_bot_variant in comment.body.lower()
            for bad_bot_variant in bad_bot_strings
        ):
            logger.warning(
                f"Bad bot detected: {self.REDDIT_BASE_URL + comment.permalink}"
            )
            return True
        return False

    def is_asking_for_block(self, comment: praw.models.Comment) -> bool:
        if "nie obchodzi mnie poprawna polszczyzna" in comment.body.lower():
            logger.warning(
                f"Asking for block: {self.REDDIT_BASE_URL + comment.permalink}"
            )
            return True
        return False

    def reply_with_retry(
        self, comment: praw.models.Comment, reply: str, max_retry: int = 3
    ) -> praw.models.Comment:
        retry_delay = 2
        for retry in range(max_retry):
            try:
                return comment.reply(reply)
            except praw.exceptions.RedditAPIException as e:
                logger.error(
                    f"Exception when replying to: {self.REDDIT_BASE_URL + comment.permalink}"
                )
                logger.error(e)
                comment.refresh()
                logger.info(f"Retrying in {retry_delay} seconds.")
                time.sleep(retry_delay)
                retry_delay *= 2

    @staticmethod
    def get_reply_probability(word: str) -> float:
        database_client = DatabaseClientSingleton()
        mean = database_client.get_mean_column("incorrect_usage")
        post_count = database_client.get_word_count(word=word, column="incorrect_usage")

        try:
            probability = min((1 / (post_count / mean)), 1)
        except ZeroDivisionError:
            probability = 1.0

        logger.debug(f"Calculated probability for {word}: {probability}")
        return probability

    def skip_comment(self, word: str) -> bool:
        random_number = random.random()
        probability = self.get_reply_probability(word=word)
        logger.info(f"Random draw for {word}: {random_number:.4f}/{probability:.4f}")
        return random_number > probability
