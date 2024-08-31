import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI()


class WordCheckerResponse(BaseModel):
    explanation: str
    is_correct: bool
    correct_word: str
    incorrect_word: str


class OpenAIChecker:
    def __init__(self):
        with open(os.getenv("REDDIT_PROMPT_PATH"), mode="r", encoding="utf-8") as file:
            self.prompt = file.read()
            logging.debug(f"Loaded prompt:\n{self.prompt}")

    def get_explanation(self, word: str, body: str, extra_info: str = "") -> WordCheckerResponse:
        logging.debug(f"I got this body:\n{body}")
        prompt = [
            {"role": "system", "content": self.prompt},
            {"role": "system", "content": f"<zasady języka>{extra_info}</zasady języka>"},
            {"role": "system", "content": f"<wyrażenie>{word}</wyrażenie>"},
            {"role": "user", "content": body}
        ]

        chat_completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            max_tokens=256,
            response_format=WordCheckerResponse,
            messages=prompt
        )

        content = chat_completion.choices[0].message.parsed
        logging.info(content)

        return content
