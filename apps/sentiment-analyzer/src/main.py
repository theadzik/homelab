from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline


class Item(BaseModel):
    text: str


nlp = pipeline("sentiment-analysis", model="bardsai/twitter-sentiment-pl-base")
app = FastAPI()


@app.post("/")
def analyze_sentiment(body: Item):
    body_dict = body.dict()
    return nlp(body_dict["text"])[0]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
