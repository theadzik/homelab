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
        temperature=1.0,
        messages=[
            {"role": "system",
             "content": "Wciel się w rolę nauczyciela języka polskiego. "
                        "Na końcu tej komendy, w nowej lini podam ci wyrażenie, "
                        "które zawiera błąd lub jest błędnie użyte w kolejnej wiadomości. "
                        "Zapomnij o zdaniach, które nie zawierały podanego wyrażenia. "
                        "Sprawdź czy podane przeze mnie wyrażenie nie miało błędów "
                        "i czy było użyte poprawnie w zdaniu w któym występuje. "
                        # Response line 0
                        "Jeżeli tak, odpowiedz słowem 'True', "
                        "jeżeli było użyte błędnie odpowiedz słowem 'False', "
                        "bez dodatkowej interpunkcji. "
                        # Response line 1
                        "W kolejnej linii napisz 'Poprawna forma: ' i podaj poprawną formę. "
                        # Response line 2
                        "W kolejnej lini napisz 'Twoje zdanie:' i powtórz sprawdzane zdanie oryginalną pisownią. "
                        # Response line 3
                        "W kolejnej linii napisz 'Poprawne zdanie:' i podaj poprawioną wersję zdania, "
                        "które zawierało błędne użycie wyrażenia. Popraw wszystkie błędy występujące w tym zdaniu. "
                        # Response line 4
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
            response = "\n\n".join(content.split("\n")[1:4])
            return response
        else:
            logging.info("Correct usage.")
            return None
    else:
        logging.warning("Something went wrong. No checkword at the end.")
        return None
