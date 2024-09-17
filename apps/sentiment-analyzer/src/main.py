import logging

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline


class Item(BaseModel):
    text: str


nlp = pipeline("sentiment-analysis", model="bardsai/twitter-sentiment-pl-base")
app = FastAPI()


@app.post("/")
def analyze_sentiment(body: Item):
    logging.debug(body)
    body_dict = body.dict()
    return nlp(body_dict["text"])[0]


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        encoding='utf-8',
        level=logging.DEBUG
    )
    uvicorn.run(app, host="0.0.0.0", port=8080)
