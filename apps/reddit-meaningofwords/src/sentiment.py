import logging
import os
from typing import Literal

import requests
from dotenv import load_dotenv
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Item(BaseModel):
    text: str


class SentimentClient:
    def __init__(self):
        self.BASE_URL = os.environ["SENTIMENT_ANALYZER_URL"]
        self.PORT = os.environ["SENTIMENT_ANALYZER_PORT"]

    def get_sentiment(self, text) -> dict:
        url = f"http://{self.BASE_URL}:{self.PORT}/"
        logger.debug(f"Got body for sentiment analysis:\n{text}")
        data = Item(text=text).dict()
        logger.debug(f"Data object:\n{data}")
        response = requests.post(url=url, json=data, headers={"Content-Type": "application/json"})
        sentiment_score = response.json()
        logger.info(f"Predicted sentiment: {sentiment_score}")
        return sentiment_score

    def is_confident_sentiment(self, text: str, sentiment: Literal["positive", "neutral", "negative"]) -> bool:
        calculated_sentiment = self.get_sentiment(text)
        return calculated_sentiment["label"] == sentiment and calculated_sentiment["score"] > 0.95


if __name__ == "__main__":
    load_dotenv()
    sentiment_client = SentimentClient()
    print(sentiment_client.get_sentiment("Ale fajny ten bot!"))
