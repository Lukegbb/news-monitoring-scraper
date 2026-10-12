"""News monitor: scrape headlines from a news page, filter them by keyword,
save a CSV report and (optionally) email it.

Settings come from command-line options or environment variables, so no
passwords live in the code. See README.md for examples.
"""
import argparse
import csv
import logging
import os
import smtplib
from dataclasses import dataclass, asdict
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("news_monitor")

DEFAULT_SELECTOR = "h2 a, h3 a"
USER_AGENT = "Mozilla/5.0 (compatible; news-monitor/2.0)"


@dataclass
class Article:
    title: str
    link: str


def fetch_html(url, timeout=10):
    """Download a page. Raises requests.RequestException on failure."""
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_articles(html, base_url, selector=DEFAULT_SELECTOR):
    """Return a list of Article from the links matched by a CSS selector.

    Relative links are turned into absolute ones and duplicates are removed.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles, seen = [], set()
    for tag in soup.select(selector):
        link_tag = tag if tag.name == "a" else tag.find("a")
        if link_tag is None or not link_tag.get("href"):
            continue
        title = " ".join(link_tag.get_text().split())
        link = urljoin(base_url, link_tag["href"])
        if title and link not in seen:
            seen.add(link)
            articles.append(Article(title, link))
    return articles


def filter_by_keywords(articles, keywords):
    """Keep articles whose title contains any keyword (case-insensitive)."""
    keywords = [k.strip().lower() for k in keywords if k.strip()]
    if not keywords:
        return list(articles)
    return [a for a in articles if any(k in a.title.lower() for k in keywords)]


def save_csv(articles, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "link"])
        writer.writeheader()
        writer.writerows(asdict(a) for a in articles)
    return path


def build_email(sender, recipient, articles, attachment_path):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = f"News report - {datetime.now():%d %b %Y} ({len(articles)} articles)"
    lines = [f"- {a.title}\n  {a.link}" for a in articles[:10]]
    msg.set_content("Latest headlines:\n\n" + "\n".join(lines) + "\n\nFull list attached.")
    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="csv",
                           filename=os.path.basename(attachment_path))
    return msg


def send_email(msg, host, port, user, password):
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Scrape headlines and email a CSV report.")
    p.add_argument("--url", default=os.getenv("NEWS_URL"), help="news page to scrape (or NEWS_URL)")
    p.add_argument("--selector", default=os.getenv("NEWS_SELECTOR", DEFAULT_SELECTOR),
                   help=f"CSS selector for headlines (default: '{DEFAULT_SELECTOR}')")
    p.add_argument("--keywords", default=os.getenv("NEWS_KEYWORDS", ""),
                   help="comma-separated keywords to filter titles")
    p.add_argument("--output", default="news_report.csv")
    p.add_argument("--email", action="store_true", help="send the report by email")
    args = p.parse_args(argv)
    if not args.url:
        p.error("--url is required (or set NEWS_URL)")
    return args


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)

    try:
        html = fetch_html(args.url)
    except requests.RequestException as exc:
        log.error("Could not download %s: %s", args.url, exc)
        return 1

    articles = filter_by_keywords(parse_articles(html, args.url, args.selector),
                                  args.keywords.split(","))
    if not articles:
        log.warning("No articles found - check the URL, selector or keywords.")
        return 0

    save_csv(articles, args.output)
    log.info("Saved %d articles to %s", len(articles), args.output)

    if args.email:
        sender = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        recipient = os.environ.get("REPORT_RECIPIENT", sender)
        if not (sender and password):
            log.error("Set SMTP_USER and SMTP_PASSWORD to send email.")
            return 1
        msg = build_email(sender, recipient, articles, args.output)
        send_email(msg, os.getenv("SMTP_HOST", "smtp.gmail.com"),
                   int(os.getenv("SMTP_PORT", "587")), sender, password)
        log.info("Report emailed to %s", recipient)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
