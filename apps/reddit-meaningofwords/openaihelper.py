import logging

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()


def openai_word_checker(word: str, body: str) -> str or None:
    chat_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "Próbuję wykryć czy prawidłowo używam słów"
                        "Podam ci słowo, które mogło, ale nie musiało być użyte błędnie. "
                        "Następnie podam ci fragment tekstu. "
                        "Sprawdź czy podane przeze mnie słowo było użyte poprawnie. Jeżeli tak, "
                        "odpowiedz słowem 'True',"
                        "jeżeli było użyte błędnie odpowiedz słowem 'False', "
                        "bez dodatkowej interpunkcji. "
                        "W kolejnej linii uzasadnij swoją odpowiedź. "
                        "W kolejnej linii podaj poprawioną wersję zdania, które zawierało błędne użycie słowa. "
                        "Popraw wszystkie błędy występujące w tym zdaniu. "
                        "Zacznij tę linię od \"Poprawne zdanie:\""
                        "W ostatniej linii napisz tylko ciąg znaków 'meaningofwords', bez dodatkowej interpunkcji."
             },
            {"role": "system", "content": word},
            {"role": "user", "content": body}
        ]
    )

    content = chat_completion.choices[0].message.content
    logging.info(content)
    if content.endswith("meaningofwords"):
        if content.startswith("False"):
            logging.info("Incorrect usage found!")
            response = "\n\n".join(content.split("\n")[1:3])
            return response
        else:
            logging.info("Correct usage.")
            return None
    else:
        logging.warning("Something went wrong. No checkword at the end.")
        return None
