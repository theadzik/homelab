import logging
import os
import sqlite3
from typing import Literal

logger = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DatabaseClient():
    def __init__(self):
        self.con = sqlite3.connect(database=os.environ["DATABASE_PATH"], timeout=10)
        self.cur = self.con.cursor()

    def get_sorted_words(self, descending: bool = False) -> list:
        query = """SELECT word FROM words
                ORDER BY incorrect_usage"""
        if descending:
            query += " DESC"
        res = self.cur.execute(query)
        return [result[0] for result in res.fetchall()]

    def increment_word_use(self, word: str, usage: Literal["incorrect_usage", "correct_usage"]):
        query = f"UPDATE words SET {usage} = {usage} + 1 WHERE word = '{word}';"
        self.cur.execute(query)
        self.con.commit()

    def save_bully(self, username: str) -> None:
        query = f"""INSERT INTO bullies VALUES
            (null, '{username}')"""
        self.cur.execute(query)
        self.con.commit()

    def is_warned_bully(self, username: str) -> bool:
        query = f"""SELECT username FROM bullies
                    WHERE username = '{username}'
                """
        res = self.cur.execute(query)
        return bool(res.fetchall())


class DatabaseClientSingleton(DatabaseClient, metaclass=Singleton):
    pass
