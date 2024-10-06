import os

import requests
from custom_logger import get_logger
from dotenv import load_dotenv
from pydantic import BaseModel

logger = get_logger(__name__)


class Item(BaseModel):
    text: str


class BullyingClient:
    def __init__(self):
        self.BASE_URL = os.environ["BULLYING_DETECTOR_URL"]
        self.PORT = os.environ["BULLYING_DETECTOR_PORT"]

    def get_bullying_prediction(self, text) -> dict:
        url = f"http://{self.BASE_URL}:{self.PORT}/"
        logger.debug(f"Got body for sentiment analysis:\n{text}")
        data = Item(text=text).dict()
        logger.debug(f"Data object:\n{data}")
        response = requests.post(url=url, json=data, headers={"Content-Type": "application/json"})
        sentiment_score = response.json()
        logger.debug(f"Predicted sentiment: {sentiment_score}")
        return sentiment_score


if __name__ == "__main__":
    load_dotenv()
    bullying_client = BullyingClient()
    print(bullying_client.get_bullying_prediction("Ale fajny ten bot!"))
