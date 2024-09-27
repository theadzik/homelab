import logging
import os
import sys

import praw
from bullying import BullyingClient
from database import DatabaseClientSingleton
from dotenv import load_dotenv
from graceful_shutdown import GracefulKiller
from openai_helper import OpenAIChecker
from reddit_bot import BotCommenter

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
bullying_analyzer = BullyingClient()
database_client = DatabaseClientSingleton()

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

    if database_client.is_banned_bully(comment.author):
        logger.info(f"Skipping comment from banned user {comment.author}")
        continue

    # Check replies to my comments
    if bot_commenter.is_my_comment_chain(comment=comment, direct=True):
        if bot_commenter.is_bad_bot_comment(comment=comment):
            logger.warning(f"Blocking user {comment.author}")
            reddit.redditor(comment.author).block()
            database_client.save_bully(username=comment.author, banned=True)
            continue

        bullying_score = bullying_analyzer.get_bullying_prediction(text=comment.body)

        if bullying_score["label"]:
            logger.warning("Bullying detected :(")
            logger.warning(f"{comment.body}")
            if not database_client.is_warned_bully(comment.author):
                openai_checker = OpenAIChecker()
                content = openai_checker.get_bullying_response(comment.body)

                if content.is_bullying:
                    logger.warning("First warning")
                    database_client.save_bully(comment.author)
                    reply_comment = comment.reply(content.response)
                else:
                    logger.warning("It wasn't bullying :D")
                    logger.warning(content)

            else:
                logger.warning(f"Second warning. Blocking bully {comment.author}")
                reddit.redditor(comment.author).block()
                database_client.save_bully(username=comment.author, banned=True)
            continue
        else:
            logger.info("No bullying :)")
            logger.debug(f"{comment.body}")
            continue

    keyword_found, match = bot_commenter.find_keywords(body=comment.body)
    if keyword_found:
        if comment.author.name == bot_commenter.bot_name:
            logger.debug("It's my own comment! Skipping.")
            continue

        if bot_commenter.is_my_comment_chain(comment):
            logger.debug("It's a reply to my comment! Skipping.")
            continue

        extra_info = bot_commenter.get_extra_info(keyword_found)
        start_index, end_index = bot_commenter.get_sentence_indexes(word=match, body=comment.body, limit=2)
        limited_body = bot_commenter.get_sentences(body=comment.body, start_index=start_index, end_index=end_index)

        logger.debug(f"Limited comment body:\n{limited_body}")
        logger.info(bot_commenter.REDDIT_BASE_URL + comment.permalink)
        logger.info(f"Calling OpenAI for explanation: {keyword_found}")

        # Initializing every time to update prompts without restarting.
        openai_checker = OpenAIChecker()
        content = openai_checker.get_explanation(body=limited_body, word=keyword_found, extra_info=extra_info)

        if not content.is_correct:
            logger.info("Phrase used incorrectly. Replying!")
            sources = bot_commenter.parse_reddit_sources(keyword_found)
            response = bot_commenter.parse_reddit_explanation(content, sources)
            reply_comment = comment.reply(response)
            logger.debug(bot_commenter.REDDIT_BASE_URL + reply_comment.permalink)
            database_client.increment_word_use(word=keyword_found, usage="incorrect_usage")
        else:
            logger.warning("Phrase used correctly. Skipping.")
            logger.warning(content)
            database_client.increment_word_use(word=keyword_found, usage="correct_usage")
