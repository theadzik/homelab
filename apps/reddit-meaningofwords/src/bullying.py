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
        data = Item(text=text).model_dump()
        logger.debug(f"Data object:\n{data}")
        try:
            response = requests.post(
                url=url, json=data, headers={"Content-Type": "application/json"}
            )
            classification = response.json()
            logger.debug(f"Classification: {classification}")
        except requests.exceptions.ConnectionError:
            logger.error("Failed to get bullying score!")
            classification = {"label": False, "score": 1.0}
            logger.warning(f"Fake negative classification: {classification}")
        return classification


if __name__ == "__main__":
    load_dotenv()
    bullying_client = BullyingClient()
    print(bullying_client.get_bullying_prediction("Ale fajny ten bot!"))
