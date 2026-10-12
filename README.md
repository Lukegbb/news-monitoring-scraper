# News Monitoring Scraper

![CI](https://github.com/Lukegbb/news-monitoring-scraper/actions/workflows/ci.yml/badge.svg)

A Python script that collects the latest headlines from a news page, filters them by keyword, saves them to a CSV file and can email the report.

I first wrote it to keep track of news about topics I follow. Version 2 is a rewrite: no hardcoded credentials, configurable selectors, keyword filtering and unit tests.

## Features

- Scrapes any news page using a CSS selector (defaults to `h2 a, h3 a`)
- Turns relative links into full URLs and removes duplicates
- Keyword filter, e.g. only headlines about `Limerick` or `AI`
- Saves a CSV report
- Optional email with the CSV attached (SMTP settings read from environment variables)
- Handles network errors and timeouts without crashing
- Unit tests that run offline against sample HTML, using GitHub Actions

## Usage

```bash
pip install -r requirements.txt

# save headlines to news_report.csv
python news_monitor.py --url https://www.rte.ie/news/ --keywords "limerick,technology"

# use a different selector for another site
python news_monitor.py --url https://example.com/news --selector "article h3 a"
```

### Sending the report by email

Set the SMTP details as environment variables. Don't put them in the code. For Gmail you need an [app password](https://support.google.com/accounts/answer/185833).

```bash
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="your-app-password"
export REPORT_RECIPIENT="someone@example.com"   # optional, defaults to SMTP_USER
python news_monitor.py --url https://www.rte.ie/news/ --email
```

| Variable | Description | Default |
|---|---|---|
| `NEWS_URL` | Page to scrape (instead of `--url`) | none |
| `NEWS_SELECTOR` | CSS selector for headlines | `h2 a, h3 a` |
| `NEWS_KEYWORDS` | Comma-separated keywords | none (all headlines) |
| `SMTP_HOST` / `SMTP_PORT` | Mail server | `smtp.gmail.com` / `587` |

You can schedule it with cron (Linux/macOS) or Task Scheduler (Windows) to get a daily report.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

## Notes

Check a website's terms and `robots.txt` before scraping it, and keep the request rate low.
