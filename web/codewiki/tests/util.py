from django.test import TestCase

from codewiki.util import SlugifyUniquely
from codewiki.models import Scraper

class ScraperUtilTests(TestCase):
    def test_scraper_list(self):
        long_title = 'I think this is a very very very very very very very long title'

        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')
        self.assertEqual('i-think-this-is-a-very-very-very-very-very-very-ve', short_name)

        scraper1 = Scraper()
        scraper1.title = long_title
        scraper1.buildfromfirsttitle()
        scraper1.save()

        self.assertEqual(short_name, scraper1.short_name)

        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')
        self.assertEqual('i-think-this-is-a-very-very-very-very-very-very-1', short_name)

        scraper2 = Scraper()
        scraper2.title = long_title
        scraper2.buildfromfirsttitle()
        scraper2.save()

        self.assertEqual(short_name, scraper2.short_name)

        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')
        self.assertEqual('i-think-this-is-a-very-very-very-very-very-very-2', short_name)
