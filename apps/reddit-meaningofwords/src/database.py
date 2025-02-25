import os
import sqlite3
from typing import Literal

from custom_logger import get_logger

logger = get_logger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DatabaseClient:
    def __init__(self):
        self.con = sqlite3.connect(database=os.environ["DATABASE_PATH"], timeout=10)
        self.cur = self.con.cursor()

    def get_mean_column(
        self, column: Literal["incorrect_usage", "correct_usage", "skipped"]
    ) -> float:
        query = f"SELECT avg({column}) FROM words WHERE enabled = 1;"
        res = self.cur.execute(query)
        return float(res.fetchone()[0])

    def get_word_count(
        self, word: str, column: Literal["incorrect_usage", "correct_usage", "skipped"]
    ):
        query = f"SELECT {column} FROM words where word = '{word}';"
        res = self.cur.execute(query)
        return int(res.fetchone()[0])

    def get_sorted_words(self, descending: bool = False) -> list:
        query = """SELECT word, incorrect_usage, correct_usage FROM words
                WHERE enabled = 1
                ORDER BY incorrect_usage"""
        if descending:
            query += " DESC"
        res = self.cur.execute(query)
        words_with_usage = res.fetchall()
        logger.debug(f"Ordered words: {words_with_usage}")
        return [row[0] for row in words_with_usage]

    def increment_word_use(
        self, word: str, usage: Literal["incorrect_usage", "correct_usage", "skipped"]
    ):
        query = f"UPDATE words SET {usage} = {usage} + 1 WHERE word = '{word}';"
        self.cur.execute(query)
        self.con.commit()

    def save_bully(self, username: str, banned: bool = False) -> None:
        query = f"""INSERT OR REPLACE INTO bullies VALUES
            (null, '{username}', {1 if banned else 0})"""
        self.cur.execute(query)
        self.con.commit()

    def is_warned_bully(self, username: str) -> bool:
        query = f"""SELECT username FROM bullies
                    WHERE username = '{username}'
                """
        res = self.cur.execute(query)
        return bool(res.fetchall())

    def is_banned_bully(self, username: str) -> bool:
        query = f"""SELECT username FROM bullies
                    WHERE username = '{username}' AND banned = 1;
                """
        res = self.cur.execute(query)
        return bool(res.fetchall())

    def save_ghost(self, username: str, reason: str) -> None:
        query = f"""INSERT INTO ghosts VALUES
            (null, '{username}', '{reason}')"""
        self.cur.execute(query)
        self.con.commit()

    def is_ghost(self, username: str) -> bool:
        query = f"""SELECT username FROM ghosts
                    WHERE username = '{username}'
                """
        res = self.cur.execute(query)
        return bool(res.fetchall())


class DatabaseClientSingleton(DatabaseClient, metaclass=Singleton):
    pass
