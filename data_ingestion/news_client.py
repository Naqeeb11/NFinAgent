import logging
import requests
from typing import List
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
        Fetches news articles related to the ticker and returns a list of NewsArticle models.
        """
        params = {
            'q': ticker,
            'apiKey': self.api_key,
            'language': 'en',
            'sortBy': 'publishedAt'
        }
        
        try:
            logger.info(f"Fetching news for {ticker}...")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                logger.error(f"News API returned error: {data.get('message')}")
                return []

            articles = []
            for item in data.get("articles", []):
                # Normalize the response to the NewsArticle model
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