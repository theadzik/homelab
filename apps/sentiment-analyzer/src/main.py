import logging
import os
import sys

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

logging.basicConfig(
    encoding='utf-8',
    level=os.getenv("LOG_LEVEL", logging.INFO),
    stream=sys.stdout
)

logger = logging.getLogger(__name__)


class Item(BaseModel):
    text: str


nlp = pipeline("sentiment-analysis", model="bardsai/twitter-sentiment-pl-base")
app = FastAPI()


@app.post("/")
def analyze_sentiment(body: Item):
    body_dict = body.dict()
    prediction = nlp(body_dict["text"])[0]
    logger.debug(f"Received body: {body_dict['text']}\nPrediction: {prediction}")
    return prediction


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
