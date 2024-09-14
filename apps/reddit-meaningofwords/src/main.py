#!/usr/bin/env python

import json
import logging
import os
import re

import nltk
import praw
from dotenv import load_dotenv
from graceful_shutdown import GracefulKiller
from openaihelper import OpenAIChecker
from openaihelper import WordCheckerResponse


class BotCommenter:
    def __init__(self):
        with open(os.getenv("REDDIT_SIGNATURE_PATH"), mode="r", encoding="utf-8") as file:
            self.signature = file.read()
            logging.debug(f"Loaded signature:\n{self.signature}")
        with open(os.getenv("REDDIT_DICTIONARY_PATH"), mode="r", encoding="utf-8") as file:
            self.words_to_check = json.load(file)

        self.patterns_to_check = {word: value.get("search_rule") for word, value in self.words_to_check.items()}
        logging.debug(f"Loaded {len(self.words_to_check)} rules.")
        self.bot_name = os.getenv("REDDIT_USERNAME")
        self.REDDIT_BASE_URL = "https://reddit.com"
        if not os.path.isdir(os.path.join(os.getenv("NLTK_DIRECTORY"), "tokenizers", "punkt_tab")):
            nltk.download('punkt_tab', download_dir=os.getenv("NLTK_DIRECTORY"))

    def find_keywords(self, body: str, skip_citations: bool = True) -> (str, str):
        for word in self.patterns_to_check.keys():
            logging.debug(f"Looking for {word}")

            if skip_citations:
                pattern = self.get_skip_citation_pattern(self.patterns_to_check.get(word))
                match_group = 1
            else:
                pattern = self.patterns_to_check.get(word)
                match_group = 0

            if match := re.search(pattern, body, flags=re.IGNORECASE | re.MULTILINE):
                logging.info(f"Found a comment with {word}!")
                logging.debug(body)
                logging.debug(match)
                logging.debug(match.group(match_group))

                return word, match.group(match_group)
        return "", ""

    @staticmethod
    def get_skip_citation_pattern(original_pattern: str) -> str:
        skip_citations_pattern = r"^(?! *?>)(?:.*?)("
        pattern = f"{skip_citations_pattern}{original_pattern})"
        return pattern

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
                logging.debug(f"Calculated start and end indexes of sentences [{start_index}:{end_index}]")
                return start_index, end_index

    @staticmethod
    def get_sentences(body: str, start_index: int, end_index: int) -> str:
        """We assume that sent_tokenize will always return the same indexes for
        normalized and non-normalized text.
        """
        all_sentences = nltk.tokenize.sent_tokenize(body, language="polish")
        relevant_sentences = " ".join(all_sentences[start_index:end_index])
        logging.debug(f"Found relevant sentences:\n{relevant_sentences}")
        return relevant_sentences

    def parse_reddt_comment(self, content: WordCheckerResponse, sources: str) -> str:
        # Add two spaces in front of the new paragraph to continue under the same bullet point.
        explanation = content.explanation.replace("\n\n", "\n\n  ")

        message = (
            f"{self.signature}"
            f"\n* Użyta forma: **{content.used_word}**"
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

    def is_my_comment_chain(self, comment: praw.models.Comment) -> bool:
        ancestor = comment
        refresh_counter = 0
        while not ancestor.is_root:
            ancestor = ancestor.parent()
            if ancestor.author == self.bot_name:
                return True
            if refresh_counter % 9 == 0:
                ancestor.refresh()
            refresh_counter += 1
        return False


load_dotenv()

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s',
        encoding='utf-8',
        level=os.getenv("LOG_LEVEL", logging.INFO)
    )

    USER_AGENT = f"linux:{os.getenv('REDDIT_USERNAME')}:{os.environ.get('APP_VERSION')} (by u/MalinowyChlopak)"
    SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "polska")

    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=USER_AGENT,
    )

    killer = GracefulKiller()

    logging.info(f"User-Agent: {USER_AGENT}")
    logging.info("Scanning comments.")

    for comment in reddit.subreddit(SUBREDDITS).stream.comments(skip_existing=True):
        # Terminating process after a new comment is received, but before anything is done with it.
        # This is because during upgrades there should already be an instance running when we get SIGTERM.
        # It's better to not post at all than to double post.
        if killer.kill_now:
            logging.info("Received kill signal. Shutting down.")
            break

        # Initializing on every loop to reload dictionary without restarting.
        bot_commenter = BotCommenter()
        logging.debug(f"Found a comment: {comment.permalink}")

        keyword_found, match = bot_commenter.find_keywords(body=comment.body)
        if keyword_found:
            if comment.author.name == bot_commenter.bot_name:
                logging.debug("It's my own comment! Skipping.")
                continue

            if bot_commenter.is_my_comment_chain(comment):
                logging.debug("It's a reply to my comment! Skipping.")
                continue

            logging.info(bot_commenter.REDDIT_BASE_URL + comment.permalink)

            extra_info = bot_commenter.get_extra_info(keyword_found)
            start_index, end_index = bot_commenter.get_sentence_indexes(word=match, body=comment.body, limit=1)
            limited_body = bot_commenter.get_sentences(body=comment.body, start_index=start_index, end_index=end_index)

            logging.info(f"Limited comment body:\n{limited_body}")

            # Initializing every time to update prompts without restarting.
            openai_checker = OpenAIChecker()
            content = openai_checker.get_explanation(body=limited_body, word=keyword_found, extra_info=extra_info)

            if not content.is_correct:
                logging.info("Phrase used incorrectly. Replying!")
                sources = bot_commenter.parse_reddit_sources(keyword_found)
                response = bot_commenter.parse_reddt_comment(content, sources)
                reply_comment = comment.reply(response)
                logging.debug(bot_commenter.REDDIT_BASE_URL + reply_comment.permalink)
            else:
                logging.warning("Phrase used correctly. Skipping.")
                logging.warning(content)
