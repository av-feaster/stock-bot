"""
News headline fetcher.
Uses free RSS feeds from Economic Times, Moneycontrol, and LiveMint.
No API key required.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import feedparser
import httpx

from config.settings import NEWS_MAX_PER_STOCK

logger = logging.getLogger("News")

# RSS feed templates keyed by source
RSS_FEEDS = {
    "economictimes": "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms",
    "moneycontrol":  "https://www.moneycontrol.com/rss/latestnews.xml",
    "livemint":      "https://www.livemint.com/rss/markets",
}

# Also do targeted Google News RSS for each ticker
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}+NSE+India+stock&hl=en-IN&gl=IN&ceid=IN:en"


class NewsFetcher:

    async def get_headlines(self, tickers: list[str]) -> dict[str, list[dict]]:
        """
        Returns {ticker: [{title, url, published}]} for each ticker.
        """
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, self._fetch_for_ticker, ticker)
            for ticker in tickers
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        results = {}
        for ticker, res in zip(tickers, results_list):
            if isinstance(res, Exception):
                logger.error("News fetch error for %s: %s", ticker, res)
                results[ticker] = []
            else:
                results[ticker] = res
        return results

    def _fetch_for_ticker(self, ticker: str) -> list[dict]:
        url = GOOGLE_NEWS_RSS.format(query=quote_plus(ticker))
        try:
            feed    = feedparser.parse(url)
            entries = feed.get("entries", [])
            cutoff  = datetime.utcnow() - timedelta(days=2)
            items   = []
            for entry in entries[:15]:   # scan first 15, keep relevant
                title = entry.get("title", "")
                link  = entry.get("link",  "#")
                pub   = entry.get("published", "")

                # Basic relevance filter — ticker name should appear in title
                if ticker.lower() not in title.lower():
                    continue

                # Clean up Google News redirect URL
                clean_link = self._clean_gnews_url(link)

                items.append({
                    "title":     title,
                    "url":       clean_link,
                    "published": pub,
                })

                if len(items) >= NEWS_MAX_PER_STOCK:
                    break

            return items

        except Exception as e:
            logger.error("RSS error for %s: %s", ticker, e)
            return []

    @staticmethod
    def _clean_gnews_url(url: str) -> str:
        """Strip Google News redirect wrapper if present."""
        match = re.search(r"url=(https?://[^&]+)", url)
        if match:
            return match.group(1)
        return url
