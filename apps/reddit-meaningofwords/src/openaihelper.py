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
    final_prompt = [
        {"role": "system",
         "content": "Podam ci wyrażenie w poprawnej lub błędnej formie.\n"
                    "Wyjaśnij jakie są zasady poprawnej pisowni tego wyrażenia.\n"
                    "Następnie sprawdź czy w tekście podanym przez użytkownika została użyta poprawna forma "
                    "w zależności od kontekstu zdania.\n"
                    "Podaj poprawną wersję zdania, które zawierało użyte wyrażenie. "
                    "Popraw wszystkie błędy występujące w tym zdaniu."
         },
        {"role": "system", "content": f"<wyrażenie>{word}</wyrażenie>"},
    ]

    if extra_info:
        final_prompt.append({"role": "system", "content": extra_info})

    final_prompt.append({"role": "user", "content": body})

    chat_completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        max_tokens=256,
        response_format=WordCheckerResponse,
        messages=final_prompt
    )

    content = chat_completion.choices[0].message.parsed
    logging.info(content)

    return content
