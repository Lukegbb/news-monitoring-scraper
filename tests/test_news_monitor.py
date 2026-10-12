import os
import tempfile
import unittest
from unittest import mock

import requests

import news_monitor as nm

SAMPLE_HTML = """
<html><body>
  <h2><a href="/tech/ai-jobs-ireland">AI jobs growing in Ireland</a></h2>
  <h2><a href="https://example.com/sport/munster">Munster win in Limerick</a></h2>
  <h3><a href="/tech/ai-jobs-ireland">AI jobs growing in Ireland</a></h3>
  <h2>No link here</h2>
  <h3><a href="/weather">  Rain   expected   tomorrow </a></h3>
</body></html>
"""
BASE = "https://example.com/news"


class ParseTests(unittest.TestCase):
    def test_parses_links_and_makes_them_absolute(self):
        articles = nm.parse_articles(SAMPLE_HTML, BASE)
        self.assertEqual(articles[0].link, "https://example.com/tech/ai-jobs-ireland")
        self.assertEqual(len(articles), 3)  # duplicate and link-less heading skipped

    def test_cleans_whitespace_in_titles(self):
        titles = [a.title for a in nm.parse_articles(SAMPLE_HTML, BASE)]
        self.assertIn("Rain expected tomorrow", titles)

    def test_custom_selector(self):
        articles = nm.parse_articles(SAMPLE_HTML, BASE, selector="h3 a")
        self.assertEqual(len(articles), 2)


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.articles = nm.parse_articles(SAMPLE_HTML, BASE)

    def test_keyword_filter_is_case_insensitive(self):
        result = nm.filter_by_keywords(self.articles, ["LIMERICK"])
        self.assertEqual([a.title for a in result], ["Munster win in Limerick"])

    def test_empty_keywords_keep_everything(self):
        self.assertEqual(len(nm.filter_by_keywords(self.articles, ["", " "])), 3)


class OutputTests(unittest.TestCase):
    def test_csv_and_email_attachment(self):
        articles = nm.parse_articles(SAMPLE_HTML, BASE)
        with tempfile.TemporaryDirectory() as tmp:
            path = nm.save_csv(articles, os.path.join(tmp, "report.csv"))
            with open(path, encoding="utf-8") as f:
                self.assertTrue(f.readline().startswith("title,link"))
            msg = nm.build_email("me@example.com", "you@example.com", articles, path)
        attachments = list(msg.iter_attachments())
        self.assertEqual(attachments[0].get_filename(), "report.csv")
        self.assertIn("3 articles", msg["Subject"])


class MainTests(unittest.TestCase):
    def test_download_error_returns_1(self):
        with mock.patch.object(nm, "fetch_html", side_effect=requests.ConnectionError("down")):
            self.assertEqual(nm.main(["--url", BASE]), 1)

    def test_email_without_credentials_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(nm, "fetch_html", return_value=SAMPLE_HTML), \
                mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(nm, "send_email") as send:
            code = nm.main(["--url", BASE, "--email", "--output", os.path.join(tmp, "r.csv")])
        self.assertEqual(code, 1)
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
