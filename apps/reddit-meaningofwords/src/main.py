import logging
import os
import sys

import praw
from dotenv import load_dotenv
from graceful_shutdown import GracefulKiller
from openai_helper import OpenAIChecker
from reddit_bot import BotCommenter
from sentiment import SentimentClient

load_dotenv()

USER_AGENT = f"linux:{os.environ['REDDIT_USERNAME']}:{os.environ['APP_VERSION']} (by u/MalinowyChlopak)"
SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "polska")

logging.basicConfig(
    encoding='utf-8',
    level=os.getenv("LOG_LEVEL", logging.INFO),
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    username=os.environ["REDDIT_USERNAME"],
    password=os.environ["REDDIT_PASSWORD"],
    user_agent=USER_AGENT,
)

killer = GracefulKiller()
sentiment_analyzer = SentimentClient()

logger.info(f"User-Agent: {USER_AGENT}")
logger.info("Scanning comments.")

for comment in reddit.subreddit(SUBREDDITS).stream.comments(skip_existing=True):
    # Terminating process after a new comment is received, but before anything is done with it.
    # This is because during upgrades there should already be an instance running when we get SIGTERM.
    # It's better to not post at all than to double post.
    if killer.kill_now:
        logger.info("Received kill signal. Shutting down.")
        break

    # Initializing on every loop to reload dictionary without restarting.
    bot_commenter = BotCommenter()
    logger.debug(f"Found a comment: {comment.permalink}")

    # Check replies to my comments
    if bot_commenter.is_my_comment_chain(comment=comment, direct=True):
        if bot_commenter.is_bad_bot_comment(comment=comment):
            logger.warning(f"Blocking user {comment.author}")
            reddit.redditor(comment.author).block()
            continue

        sentiment_score = sentiment_analyzer.get_sentiment(text=comment.body)

        match sentiment_score["label"]:
            case "negative":
                logger.warning("Got a negative comment :(")
                logger.warning(f"{comment.body}")
                continue
            case "neutral":
                logger.warning("Got a neutral comment :|")
                logger.warning(f"{comment.body}")
                continue
            case "positive":
                logger.warning("Got a positive comment :)")
                logger.warning(f"{comment.body}")
                continue

    keyword_found, match = bot_commenter.find_keywords(body=comment.body)
    if keyword_found:
        if comment.author.name == bot_commenter.bot_name:
            logger.debug("It's my own comment! Skipping.")
            continue

        if bot_commenter.is_my_comment_chain(comment):
            logger.debug("It's a reply to my comment! Skipping.")
            continue

        logger.info(bot_commenter.REDDIT_BASE_URL + comment.permalink)
        logger.info(f"Checking comment for correct usage of word: {keyword_found}")

        extra_info = bot_commenter.get_extra_info(keyword_found)
        start_index, end_index = bot_commenter.get_sentence_indexes(word=match, body=comment.body, limit=2)
        limited_body = bot_commenter.get_sentences(body=comment.body, start_index=start_index, end_index=end_index)

        logger.info(f"Limited comment body:\n{limited_body}")

        # Initializing every time to update prompts without restarting.
        openai_checker = OpenAIChecker()
        content = openai_checker.get_explanation(body=limited_body, word=keyword_found, extra_info=extra_info)

        if not content.is_correct:
            logger.info("Phrase used incorrectly. Replying!")
            sources = bot_commenter.parse_reddit_sources(keyword_found)
            response = bot_commenter.parse_reddt_comment(content, sources)
            reply_comment = comment.reply(response)
            logger.debug(bot_commenter.REDDIT_BASE_URL + reply_comment.permalink)
        else:
            logger.warning("Phrase used correctly. Skipping.")
            logger.warning(content)
