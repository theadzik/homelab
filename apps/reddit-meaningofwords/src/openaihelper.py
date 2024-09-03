import logging
import os

import openai
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

client = openai.OpenAI()


class WordCheckerResponse(BaseModel):
    explanation: str
    is_correct: bool
    correct_word: str
    incorrect_word: str
    corrected_sentence: str


class OpenAIChecker:
    def __init__(self):
        with open(os.getenv("REDDIT_PROMPT_PATH"), mode="r", encoding="utf-8") as file:
            self.prompt = file.read()
            logging.debug(f"Loaded prompt:\n{self.prompt}")

        self.presence_penalty = float(os.getenv("OPEN_AI_PRESENCE_PENALTY", 0))
        self.frequency_penalty = float(os.getenv("OPEN_AI_FREQUENCY_PENALTY", 0))
        self.temperature = float(os.getenv("OPEN_AI_TEMPERATURE", 1))

    def get_explanation(self, word: str, body: str, extra_info: str = "") -> WordCheckerResponse:
        logging.debug(f"I got this body:\n{body}")
        prompt = [
            {"role": "system", "content": self.prompt},
            {"role": "system", "content": f"<zasady>{extra_info}</zasady>"},
            {"role": "system", "content": f"<wyrażenie>{word}</wyrażenie>"},
            {"role": "user", "content": body}
        ]
        try:
            chat_completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                max_tokens=256,
                response_format=WordCheckerResponse,
                messages=prompt,
                presence_penalty=self.presence_penalty,
                frequency_penalty=self.frequency_penalty,
                temperature=self.temperature,
            )
        except openai.LengthFinishReasonError as e:
            logging.error("Generated response was too long!")
            logging.error(e)
            logging.info("Retrying with higher limit.")
            chat_completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                max_tokens=512,
                response_format=WordCheckerResponse,
                messages=prompt,
                presence_penalty=self.presence_penalty,
                frequency_penalty=self.frequency_penalty,
                temperature=self.temperature,
            )

        content = chat_completion.choices[0].message.parsed
        logging.info(content)

        return content
