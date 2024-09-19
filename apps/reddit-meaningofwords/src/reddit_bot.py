import json
import logging
import os
import random
import re

import nltk
import praw
from openai_helper import WordCheckerResponse

logger = logging.getLogger(__name__)


class BotCommenter:
    def __init__(self):
        with open(os.environ["REDDIT_SIGNATURE_PATH"], mode="r", encoding="utf-8") as file:
            self.signature = file.read()
            logger.debug(f"Loaded signature:\n{self.signature}")
        with open(os.environ["REDDIT_DICTIONARY_PATH"], mode="r", encoding="utf-8") as file:
            self.words_to_check = json.load(file)

        self.patterns_to_check = {word: value.get("search_rule") for word, value in self.words_to_check.items()}
        logger.debug(f"Loaded {len(self.words_to_check)} rules.")
        self.bot_name = os.environ["REDDIT_USERNAME"]
        self.REDDIT_BASE_URL = "https://reddit.com"
        if not os.path.isdir(os.path.join(os.environ["NLTK_DIRECTORY"], "tokenizers", "punkt_tab")):
            nltk.download('punkt_tab', download_dir=os.environ["NLTK_DIRECTORY"])

    def find_keywords(self, body: str, skip_citations: bool = True, random_order: bool = True) -> (str, str):
        words = list(self.patterns_to_check.keys())
        if random_order:
            random.shuffle(words)

        for word in words:
            logger.debug(f"Looking for {word}")

            if skip_citations:
                pattern = self.get_skip_citation_pattern(self.patterns_to_check.get(word))
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
                logger.debug(f"Calculated start and end indexes of sentences [{start_index}:{end_index}]")
                return start_index, end_index

    @staticmethod
    def get_sentences(body: str, start_index: int, end_index: int) -> str:
        """We assume that sent_tokenize will always return the same indexes for
        normalized and non-normalized text.
        """
        all_sentences = nltk.tokenize.sent_tokenize(body, language="polish")
        relevant_sentences = " ".join(all_sentences[start_index:end_index])
        logger.debug(f"Found relevant sentences:\n{relevant_sentences}")
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

    def is_my_comment_chain(self, comment: praw.models.Comment, direct: bool = False) -> bool:
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
        if comment.body.lower().startswith("bad bot"):
            logger.warning(f"Bad bot detected: {self.REDDIT_BASE_URL + comment.permalink}")
            return True
        return False