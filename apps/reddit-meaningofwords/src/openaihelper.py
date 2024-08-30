import logging

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI()


class WordCheckerResponse(BaseModel):
    incorrect_word: str
    correct_word: str
    explanation: str
    corrected_sentence: str


def openai_word_checker(word: str, body: str) -> WordCheckerResponse:
    chat_completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        max_tokens=256,
        response_format=WordCheckerResponse,
        messages=[
            {"role": "system",
             "content": "Na końcu tej komendy podam ci wyrażenie. "
                        "Sprawdź czy było użyte poprawnie w zdaniu w któym występuje. \n"
                        "Podaj formę niepoprawnie użytą w zdaniu.\n"
                        "Podaj poprawną formę.\n"
                        "Podaj wyjaśnienie na maksymalnie dwa zdania.\n"
                        "Podaj poprawioną wersję zdania, które zawierało błędne użycie wyrażenie. "
                        "Popraw wszystkie błędy występujące w tym zdaniu."
             },
            {"role": "system", "content": f"<wyrażenie>{word}</wyrażenie>"},
            {"role": "user", "content": body}
        ]
    )

    content = chat_completion.choices[0].message.parsed
    logging.info(content)

    return content
