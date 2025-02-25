import unittest

from main import BotCommenter


class TestBotCommenter(unittest.TestCase):
    def test_find_keyword_conajmniej(self):
        bot = BotCommenter()
        text = r"Lubię frytki cOnAJmniej, tak bardzo jak czekoladę!"
        keyword_found, match = bot.find_keywords(text)
        self.assertEqual(keyword_found, "co najmniej")
        self.assertEqual(match, "cOnAJmniej")

    def test_find_keyword_dlatego_ze(self):
        bot = BotCommenter()
        text = r"Lubię frytki dlaTEgo, bo są z ziemniaka."
        keyword_found, match = bot.find_keywords(text)
        self.assertEqual(keyword_found, "dlatego że")
        self.assertEqual(match, "dlaTEgo, bo")

    def test_find_keyword_dopoki(self):
        bot = BotCommenter()
        text1 = r"Do pOki masz czas."
        text2 = r"Do pÓki, masz czas."
        text3 = r"Cześć. Do pUki masz czas."
        text4 = r"Dopuki"

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found3, match3 = bot.find_keywords(text3)
        keyword_found4, match4 = bot.find_keywords(text4)

        self.assertEqual(keyword_found1, "dopóki")
        self.assertEqual(match1, "Do pOki")

        self.assertEqual(keyword_found2, "dopóki")
        self.assertEqual(match2, "Do pÓki")

        self.assertEqual(keyword_found3, "dopóki")
        self.assertEqual(match3, "Do pUki")

        self.assertEqual(keyword_found4, "dopóki")
        self.assertEqual(match4, "Dopuki")

    def test_skip_citations_dopoki(self):
        bot = BotCommenter()
        text1 = r"Do pOki masz czas."
        text1c = r">Do pOki masz czas."
        text2 = r"Do pÓki, masz czas."
        text2c = r" > Do pÓki, masz czas."
        text3 = "Usunięty komentarz brzmiał:\n\nLubię lody do póki są czekoladowe"
        text3c = "Usunięty komentarz brzmiał:\n\n>Lubię lody do póki są czekoladowe"
        text4 = (
            "Usunięty komentarz brzmiał:\n\ndo póki są czekoladowe, dopóty je lubię."
        )
        text4c = (
            "Usunięty komentarz brzmiał:\n\n>do póki są czekoladowe, dopóty je lubię."
        )

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found1c, match1c = bot.find_keywords(text1c)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found2c, match2c = bot.find_keywords(text2c)
        keyword_found3, match3 = bot.find_keywords(text3)
        keyword_found3c, match3c = bot.find_keywords(text3c)
        keyword_found4, match4 = bot.find_keywords(text4)
        keyword_found4c, match4c = bot.find_keywords(text4c)

        self.assertEqual(keyword_found1, "dopóki")
        self.assertEqual(match1, "Do pOki")

        self.assertEqual(keyword_found1c, "")
        self.assertEqual(match1c, "")

        self.assertEqual(keyword_found2, "dopóki")
        self.assertEqual(match2, "Do pÓki")

        self.assertEqual(keyword_found2c, "")
        self.assertEqual(match2c, "")

        self.assertEqual(keyword_found3, "dopóki")
        self.assertEqual(match3, "do póki")

        self.assertEqual(keyword_found3c, "")
        self.assertEqual(match3c, "")

        self.assertEqual(keyword_found4, "dopóki")
        self.assertEqual(match4, "do póki")

        self.assertEqual(keyword_found4c, "")
        self.assertEqual(match4c, "")

    def test_find_keyword_dzisiaj(self):
        bot = BotCommenter()
        text1 = r"W dniu dzisiejszym"
        text2 = r"`DzieŃ wczorajszy` był fajny."
        text3 = r"Co przyniesie dzieN jutrzejszy?"

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found3, match3 = bot.find_keywords(text3)

        self.assertEqual(keyword_found1, "dzisiaj/obecnie")
        self.assertEqual(match1, "dniu dzisiejszym")

        self.assertEqual(keyword_found2, "dzisiaj/obecnie")
        self.assertEqual(match2, "DzieŃ wczorajszy")

        self.assertEqual(keyword_found3, "dzisiaj/obecnie")
        self.assertEqual(match3, "dzieN jutrzejszy")

    def test_find_keyword_linia_oporu(self):
        bot = BotCommenter()
        text1 = r"Pojadę najmniejszą linią oporu"
        text2 = r"`__+==wiĘKSZĄ LINIĄ OPoru"
        text3 = r"mnIEJSZej linii OPORU"

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found3, match3 = bot.find_keywords(text3)

        self.assertEqual(keyword_found1, "linia najmniejszego oporu")
        self.assertEqual(match1, "najmniejszą linią oporu")

        self.assertEqual(keyword_found2, "linia najmniejszego oporu")
        self.assertEqual(match2, "wiĘKSZĄ LINIĄ OPoru")

        self.assertEqual(keyword_found3, "linia najmniejszego oporu")
        self.assertEqual(match3, "mnIEJSZej linii OPORU")

    def test_find_keyword_optymalny(self):
        bot = BotCommenter()
        text1 = r"Najoptymalniejszą drogą będzie."
        text2 = r"Po co to robić bardziej optymalnie?"
        text3 = r"Czy ona jest najbardziej optymalniejsza?"
        text4 = r"Czy ona jest najmniej optymalną?"

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found3, match3 = bot.find_keywords(text3)
        keyword_found4, match4 = bot.find_keywords(text4)

        self.assertEqual(keyword_found1, "optymalny")
        self.assertEqual(match1, "Najoptymalniejszą")

        self.assertEqual(keyword_found2, "optymalny")
        self.assertEqual(match2, "bardziej optymalnie")

        self.assertEqual(keyword_found3, "optymalny")
        self.assertEqual(match3, "najbardziej optymalniejsza")

        self.assertEqual(keyword_found4, "optymalny")
        self.assertEqual(match4, "najmniej optymalną")

    def test_no_keywords(self):
        bot = BotCommenter()
        text1 = r"Lubię kredki a optymalną drogą będzie."
        text2 = r"Po co to robić bardziej na pewno?"
        text3 = r"Czy ona jest poprawna dopóki jest?"
        text4 = r"Czy ona jest kosmitką?"

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found3, match3 = bot.find_keywords(text3)
        keyword_found4, match4 = bot.find_keywords(text4)

        self.assertEqual(keyword_found1, "")
        self.assertEqual(match1, "")

        self.assertEqual(keyword_found2, "")
        self.assertEqual(match2, "")

        self.assertEqual(keyword_found3, "")
        self.assertEqual(match3, "")

        self.assertEqual(keyword_found4, "")
        self.assertEqual(match4, "")


if __name__ == "__main__":
    unittest.main()
