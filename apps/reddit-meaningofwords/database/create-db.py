import json
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

con = sqlite3.connect(os.environ["DATABASE_PATH"], timeout=10)
cur = con.cursor()
cur.execute('PRAGMA encoding="UTF-8"')
cur.execute(""" CREATE TABLE IF NOT EXISTS words(
                id integer PRIMARY KEY,
                word text UNIQUE,
                incorrect_usage integer,
                correct_usage integer
                ); """
            )

res = cur.execute("SELECT name FROM sqlite_master")
res.fetchone()

with open(os.environ["REDDIT_DICTIONARY_PATH"], mode="r", encoding="utf-8", ) as dictionary:
    words_to_check = json.load(dictionary)

i = 0
for word in words_to_check.keys():
    i += 1

    cur.execute(f"""
        INSERT OR IGNORE INTO words VALUES
            ({i}, '{word}', 0, 0)
    """)

    con.commit()
