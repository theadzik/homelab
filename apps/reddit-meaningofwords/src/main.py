import os
import time

import praw
from bullying import BullyingClient
from custom_logger import get_logger
from database import DatabaseClientSingleton
from dotenv import load_dotenv
from openai_helper import OpenAIChecker
from prawcore import RequestException
from prawcore import ServerError
from reddit_bot import BotCommenter

load_dotenv()

USER_AGENT = f"linux:{os.environ['REDDIT_USERNAME']}:{os.environ['APP_VERSION']} (by u/MalinowyChlopak)"
SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "polska")

logger = get_logger(__name__)
liveness_probe = os.getenv("LIVENESS_FILE_PATH", "/tmp/liveness")

reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    username=os.environ["REDDIT_USERNAME"],
    password=os.environ["REDDIT_PASSWORD"],
    user_agent=USER_AGENT,
)

bullying_analyzer = BullyingClient()
database_client = DatabaseClientSingleton()
bot_commenter = BotCommenter()
openai_checker = OpenAIChecker()

logger.info(f"User-Agent: {USER_AGENT}")
logger.info("Scanning comments.")


def handle_keyword(
    comment: praw.models.Comment, keyword_found: str, match: str
) -> None:
    if comment.author.name == bot_commenter.bot_name:
        logger.debug("It's my own comment! Skipping.")
        return

    if bot_commenter.is_my_comment_chain(comment):
        logger.debug("It's a reply to my comment! Skipping.")
        return

    if bot_commenter.skip_comment(word=keyword_found):
        logger.info(f"Skipping common word: {keyword_found}!")
        database_client.increment_word_use(word=keyword_found, usage="skipped")
        return

    extra_info = bot_commenter.get_extra_info(keyword_found)

    logger.info(bot_commenter.REDDIT_BASE_URL + comment.permalink)
    logger.info(f"Calling OpenAI for explanation: {keyword_found}")

    content = openai_checker.get_explanation(
        body=comment.body, word=keyword_found, extra_info=extra_info
    )

    if not content.is_correct:
        logger.info(f"{content.used_word} used incorrectly. Replying!")
        sources = bot_commenter.parse_reddit_sources(keyword_found)
        response = bot_commenter.parse_reddit_explanation(content, sources)
        _ = bot_commenter.reply_with_retry(comment=comment, reply=response)
        database_client.increment_word_use(word=keyword_found, usage="incorrect_usage")
    else:
        logger.warning(f"{content.used_word} used correctly. Skipping.")
        logger.warning(content)
        database_client.increment_word_use(word=keyword_found, usage="correct_usage")


def handle_direct_reply(comment: praw.models.Comment) -> None:
    logger.info(bot_commenter.REDDIT_BASE_URL + comment.permalink)
    if bot_commenter.is_asking_for_block(comment=comment):
        logger.warning(f"Blocking user {comment.author}")
        reddit.redditor(comment.author).block()
        database_client.save_bully(username=comment.author, banned=True)
        return

    if bot_commenter.is_bad_bot_comment(comment=comment):
        if database_client.is_ghost(comment.author):
            logger.info(f"{comment.author} is a ghost. Skipping.")
            return
        logger.warning("Bad bot detected :(")
        content = openai_checker.get_bad_bot_response(comment.body)
        _ = bot_commenter.reply_with_retry(comment=comment, reply=content.response)
        database_client.save_ghost(comment.author, "Bad bot comment")
        return

    bullying_score = bullying_analyzer.get_bullying_prediction(text=comment.body)

    if bullying_score["label"]:
        logger.warning("Bullying detected :(")
        logger.warning(f"{comment.body}")
        if not database_client.is_warned_bully(comment.author):
            content = openai_checker.get_bullying_response(comment.body)

            if content.is_bullying:
                logger.warning("First warning")
                database_client.save_bully(comment.author)
                _ = bot_commenter.reply_with_retry(
                    comment=comment, reply=content.response
                )
            else:
                logger.warning("It wasn't bullying :D")
                logger.warning(content)

        else:
            logger.warning(f"Second warning. Blocking bully {comment.author}")
            reddit.redditor(comment.author).block()
            database_client.save_bully(username=comment.author, banned=True)
        return
    else:
        logger.info("No bullying :)")
        logger.debug(f"{comment.body}")
        return


def handle_comment(comment: praw.models.Comment) -> None:
    logger.debug(f"Found a comment: {comment.permalink}")

    if database_client.is_banned_bully(comment.author):
        logger.debug(f"Skipping comment from banned user {comment.author}")
        return

    # Check replies to my comments
    if bot_commenter.is_my_comment_chain(comment=comment, direct=True):
        handle_direct_reply(comment=comment)

    keyword_found, match = bot_commenter.find_keywords(body=comment.body)
    if keyword_found:
        handle_keyword(comment=comment, keyword_found=keyword_found, match=match)


# Main loop
while True:
    try:
        for comment in reddit.subreddit(SUBREDDITS).stream.comments(skip_existing=True):
            # Create a file for liveness probe
            with open(liveness_probe, mode="a"):
                pass
            handle_comment(comment=comment)
    except (ServerError, RequestException) as e:
        logger.error(e)
        logger.info("Waiting 60 seconds.")
        time.sleep(60)
