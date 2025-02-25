import json
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

con = sqlite3.connect(os.environ["DATABASE_PATH"], timeout=10)
cur = con.cursor()
cur.execute('PRAGMA encoding="UTF-8"')
cur.execute(
    """CREATE TABLE IF NOT EXISTS words(
                                        id integer PRIMARY KEY,
                                        word text UNIQUE,
                                        incorrect_usage integer,
                                        correct_usage integer,
                                        skipped integer,
                                        enabled integer
                                        ); """
)

cur.execute(
    """CREATE TABLE IF NOT EXISTS bullies(
                                            id integer PRIMARY KEY,
                                            username text UNIQUE,
                                            banned integer
                                          );"""
)

cur.execute(
    """CREATE TABLE IF NOT EXISTS ghosts(
                                            id integer PRIMARY KEY,
                                            username text UNIQUE,
                                            reason text
                                          );"""
)

with open(
    os.environ["REDDIT_DICTIONARY_PATH"],
    mode="r",
    encoding="utf-8",
) as dictionary:
    words_to_check = json.load(dictionary)

i = 0
for word in words_to_check.keys():
    i += 1

    cur.execute(
        f"""INSERT OR IGNORE INTO words VALUES
            (null, '{word}', 0, 0, 0, 1);"""
    )

    con.commit()
