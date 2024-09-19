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
    used_word: str
    correct_word: str


class BullyingDetectorResponse(BaseModel):
    is_bullying: bool
    response: str


class OpenAIChecker:
    def __init__(self):
        with open(os.getenv("REDDIT_CHECKER_PROMPT_PATH"), mode="r", encoding="utf-8") as file:
            self.checker_prompt = file.read()
            logging.debug(f"Loaded checker prompt:\n{self.checker_prompt}")

        with open(os.getenv("REDDIT_BULLY_PROMPT_PATH"), mode="r", encoding="utf-8") as file:
            self.bully_prompt = file.read()
            logging.debug(f"Loaded bully prompt:\n{self.bully_prompt}")

        self.presence_penalty = float(os.getenv("OPEN_AI_PRESENCE_PENALTY", 0))
        self.frequency_penalty = float(os.getenv("OPEN_AI_FREQUENCY_PENALTY", 0))
        self.temperature = float(os.getenv("OPEN_AI_TEMPERATURE", 1))

    def send_request(self, prompt: list, response_format: type[BaseModel]):
        max_tokens = 256
        for attempt in range(2):
            try:
                chat_completion = client.beta.chat.completions.parse(
                    model="gpt-4o-2024-08-06",
                    max_tokens=max_tokens,
                    response_format=response_format,
                    messages=prompt,
                    presence_penalty=self.presence_penalty,
                    frequency_penalty=self.frequency_penalty,
                    temperature=self.temperature,
                )
                content = chat_completion.choices[0].message.parsed
                logging.info(content)

                return content
            except openai.LengthFinishReasonError as e:
                logging.error(f"Generated response was longer than {max_tokens} tokens!")
                logging.error(e)
                max_tokens += 256
                logging.info(f"Retrying with higher limit: {max_tokens}")

    def get_bullying_response(self, body: str) -> BullyingDetectorResponse:
        logging.debug(f"I got this body:\n{body}")

        prompt = [
            {"role": "system", "content": self.bully_prompt},
            {"role": "user", "content": body}
        ]

        return self.send_request(prompt=prompt, response_format=BullyingDetectorResponse)

    def get_explanation(self, word: str, body: str, extra_info: str = "") -> WordCheckerResponse:
        logging.debug(f"I got this body:\n{body}")
        prompt = [
            {"role": "system", "content": self.checker_prompt},
            {"role": "system", "content": f"<zasady>{extra_info}</zasady>"},
            {"role": "system", "content": f"<wyrażenie>{word}</wyrażenie>"},
            {"role": "user", "content": body}
        ]

        return self.send_request(prompt=prompt, response_format=WordCheckerResponse)
