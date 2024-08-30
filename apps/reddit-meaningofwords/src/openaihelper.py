import logging

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()


def openai_word_checker(word: str, body: str) -> str or None:
    # TODO: use json schema instead of prompt
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=256,
        messages=[
            {"role": "system",
             "content": "Na końcu tej komendy, w nowej lini podam ci wyrażenie, "
                        "które zawiera błąd lub jest błędnie użyte w kolejnej wiadomości. "
                        "Zapomnij o zdaniach, które nie zawierały podanego wyrażenia. "
                        "Nie odnoś się do, ani nie powtarzaj pozostałych zdań nigdzie w swojej odpowiedzi. "
                        "Sprawdź czy podane przeze mnie wyrażenie nie miało błędów "
                        "i czy było użyte poprawnie w zdaniu w któym występuje. \n"
             # Response line 0
                        "Jeżeli tak, odpowiedz słowem 'True', "
                        "jeżeli było użyte błędnie odpowiedz słowem 'False', "
                        "bez dodatkowej interpunkcji.\n"
             # Response line 1
                        "W kolejnej linii napisz '* Niepoprawna forma: ' i podaj formę niepoprawnie użytą w zdaniu.\n"
             # Response line 2
                        "W kolejnej linii napisz '* Poprawna forma: ' i podaj poprawną formę.\n"
             # Response line 3
                        "W kolejnej linii napisz '* Wyjaśnienie: ' i wyjaśnij dlaczego użyta forma jest niepoprawna.\n"
             # Response line 4
                        "W kolejnej linii napisz '* Poprawne zdanie:' i podaj poprawioną wersję zdania, "
                        "które zawierało błędne użycie wyrażenia. Popraw wszystkie błędy występujące w tym zdaniu. \n"
             # Response line 5
                        "W ostatniej linii napisz tylko ciąg znaków 'meaningofwords', bez dodatkowej interpunkcji."
             },
            {"role": "system", "content": f"<wyrażenie>{word}</wyrażenie>"},
            {"role": "user", "content": body}
        ]
    )

    content = chat_completion.choices[0].message.content
    logging.info(content)
    if content.endswith("meaningofwords"):
        if content.startswith("False"):
            logging.info("Incorrect usage found!")
            response = "\n\n".join(content.split("\n")[1:-1])
            return response
        else:
            logging.info("Correct usage.")
            return None
    else:
        logging.warning("Something went wrong. No checkword at the end.")
        logging.warning(f"Comment:\n{body}")
        logging.warning(f"Reply content:\n{content}")
        return None
