import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from data_ingestion.news_client import NewsClient
from db.models import NewsArticle

def test_fetch_news_normalization():
    """
    Test that news data is correctly normalized into NewsArticle models.
    """
    ticker = "AAPL"
    mock_response = {
        "status": "ok",
        "articles": [
            {
                "url": "http://example.com/article1",
                "title": "Apple launches new iPhone",
                "description": "Apple revealed its latest device today.",
                "publishedAt": "2023-10-01T10:00:00Z",
                "source": {"name": "TechCrunch"}
            }
        ]
    }
    
    client = NewsClient()
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        results = client.fetch_news(ticker)
        
        assert len(results) == 1
        article = results[0]
        assert isinstance(article, NewsArticle)
        assert article.ticker == ticker
        assert article.title == "Apple launches new iPhone"
        assert article.source == "TechCrunch"
        assert article.article_id == "http://example.com/article1"