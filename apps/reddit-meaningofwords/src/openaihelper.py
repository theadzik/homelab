import logging

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI()


class WordCheckerResponse(BaseModel):
    explanation: str
    is_correct: bool
    corrected_sentence: str
    correct_word: str
    incorrect_word: str


def openai_word_checker(word: str, body: str, extra_info: str = "") -> WordCheckerResponse:
    logging.debug(f"I got this body:\n{body}")
    prompt = [
        {"role": "system",
         "content": "Podam ci wyrażenie w poprawnej lub błędnej formie.\n"
                    "Nastpęnie podam ci zasady języka polskiego dotyczące tego lub podobnych wyrażeń.\n"
                    "Sprawdź czy podanym przeze mnie tekście zostanie użyta poprawna forma "
                    "w zależności od kontekstu zdania.\n"
                    "Wyjaśnij jakie zasady poprawnej pisowni dotyczną tego wyrażenia, "
                    "opierając się o zasady, które ci podam.\n"
                    "Podaj poprawną wersję zdania, które zawierało użyte wyrażenie. "
                    "Ogranicz się tylko do tego jednego zdania. "
                    "Popraw wszystkie błędy występujące w tym zdaniu, włączając błędy interpunkcyjne."
         },
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
