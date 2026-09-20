import logging
import requests
from typing import List, Optional
from datetime import datetime
from db.models import NewsArticle
from config.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsClient:
    """
    Client to fetch financial news articles for a specific ticker.
    Designed to work with NewsAPI.org or similar REST APIs.
    """
    def __init__(self):
        self.api_key = config.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2/everything"

    def fetch_news(self, ticker: str) -> List[NewsArticle]:
        """
        Fetches general recent news articles related to the ticker,
        sorted by publish date.
        """
        logger.info(f"Fetching news for {ticker}...")
        return self._request(
            query=ticker,
            ticker=ticker,
            sort_by='publishedAt',
            page_size=None,
        )

    def search_news(self, ticker: str, query: str, limit: int = 3) -> List[NewsArticle]:
        """
        Searches news for a specific concern related to the ticker
        (e.g. query='lawsuits' or 'supply chain'), sorted by relevancy.
        Used by ResearchAgent's targeted follow-up tool calls.
        """
        combined_query = f"{ticker} {query}"
        logger.info(f"Searching news for {ticker} with query: {query}")
        return self._request(
            query=combined_query,
            ticker=ticker,
            sort_by='relevancy',
            page_size=limit,
        )

    def _request(self, query: str, ticker: str, sort_by: str, page_size: Optional[int]) -> List[NewsArticle]:
        """
        Shared request/parsing logic for fetch_news and search_news, so both
        go through the same error handling and NewsArticle normalization.
        """
        params = {
            'q': query,
            'apiKey': self.api_key,
            'language': 'en',
            'sortBy': sort_by,
        }
        if page_size:
            params['pageSize'] = page_size

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.error(f"News API returned error: {data.get('message')}")
                return []

            items = data.get("articles", [])
            if page_size:
                items = items[:page_size]

            articles = []
            for item in items:
                article = NewsArticle(
                    article_id=item.get("url"),
                    ticker=ticker,
                    title=item.get("title", "No Title"),
                    content=item.get("description", ""),
                    source=item.get("source", {}).get("name", "Unknown"),
                    published_at=self._parse_date(item.get("publishedAt"))
                )
                articles.append(article)

            return articles

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching news for {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching news for {ticker}: {e}")
            return []

    def _parse_date(self, date_str: str) -> datetime:
        """Helper to parse ISO format date strings."""
        if not date_str:
            return datetime.utcnow()
        try:
            # Handles '2023-10-01T10:00:00Z'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return datetime.utcnow()