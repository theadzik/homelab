import logging
import os
import sys
from enum import Enum

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


class Bullying(Enum):
    LABEL_0 = False
    LABEL_1 = True


# The model checks if text is cyberbullying (LABEL_1) or not (LABEL_0)
nlp = pipeline("text-classification", model="ptaszynski/bert-base-polish-cyberbullying")
app = FastAPI()


@app.post("/")
def detect_bullying(body: Item):
    body_dict = body.dict()
    prediction = nlp(body_dict["text"])[0]
    prediction["label"] = Bullying[prediction["label"]].value
    logger.debug(f"Received body: {body_dict['text']}\nPrediction: {prediction}")
    return prediction


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
