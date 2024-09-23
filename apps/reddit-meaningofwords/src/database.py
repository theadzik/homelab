import os
import sqlite3
from typing import Literal


class DatabaseClient:
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


if __name__ == "__main__":
    db_client = DatabaseClient()
    print(db_client.get_sorted_words())
    db_client.increment_word_use("notabene", "incorrect_usage")
    print(db_client.get_sorted_words())
