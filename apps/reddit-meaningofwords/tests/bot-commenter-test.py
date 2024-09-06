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

    def test_find_keyword_dzisiaj(self):
        bot = BotCommenter()
        text1 = r"W dniu dzisiejszym"
        text2 = r"`DzieŃ wczorajszy` był fajny."
        text3 = r"Co przyniesie dzieN jutrzejszy?"

        keyword_found1, match1 = bot.find_keywords(text1)
        keyword_found2, match2 = bot.find_keywords(text2)
        keyword_found3, match3 = bot.find_keywords(text3)

        self.assertEqual(keyword_found1, "dzisiaj")
        self.assertEqual(match1, "dniu dzisiejszym")

        self.assertEqual(keyword_found2, "dzisiaj")
        self.assertEqual(match2, "DzieŃ wczorajszy")

        self.assertEqual(keyword_found3, "dzisiaj")
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


if __name__ == '__main__':
    unittest.main()
