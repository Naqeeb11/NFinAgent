import logging
import ollama
from typing import List, Dict, Any
from datetime import datetime, timedelta

from data_ingestion.alpaca_client import AlpacaClient
from data_ingestion.yfinance_client import YFinanceClient
from data_ingestion.edgar_client import EdgarClient
from data_ingestion.news_client import NewsClient
from ml.sentiment_scorer import SentimentScorer
from config.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchAgent:
    """
    ResearchAgent integrates multiple data sources and an LLM to provide 
    comprehensive financial research and analysis for a given ticker.
    """
    def __init__(self):
        self.alpaca_client = AlpacaClient()
        self.yfinance_client = YFinanceClient()
        self.edgar_client = EdgarClient()
        self.news_client = NewsClient()
        self.sentiment_scorer = SentimentScorer()
        self.llm_model = config.OLLAMA_MODEL

    def gather_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collects historical prices, news, and filings for a ticker.
        """
        logger.info(f"Gathering data for {ticker}...")
        
        # Dates for historical data (last 30 days)
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Fetch price data (prefer Alpaca, fallback to yfinance)
        prices = self.alpaca_client.get_historical_prices(ticker, start_date, end_date)
        if not prices:
            logger.info(f"Alpaca returned no data for {ticker}, trying yfinance...")
            prices = self.yfinance_client.get_historical_prices(ticker, start_date, end_date)

        # Fetch news
        news = self.news_client.fetch_news(ticker)
        
        # Score news sentiment
        sentiment_summaries = []
        for article in news:
            score = self.sentiment_scorer.score_text(article.content, getattr(article, 'article_id', 0))
            sentiment_summaries.append({
                'title': article.title,
                'sentiment': score.label,
                'confidence': score.confidence
            })

        # Fetch filings (latest 10-K/10-Q)
        filings = self.edgar_client.download_filings(ticker, '10-K') + \
                  self.edgar_client.download_filings(ticker, '10-Q')

        return {
            'ticker': ticker,
            'prices': prices,
            'news_sentiment': sentiment_summaries,
            'filings': filings,
            'start_date': start_date,
            'end_date': end_date
        }

    def analyze(self, ticker: str) -> str:
        """
        Gather data and use Ollama to generate a research report.
        """
        data = self.gather_data(ticker)
        
        # Prepare a summary for the LLM
        price_summary = ""
        if data['prices']:
            last_price = data['prices'][-1].close
            first_price = data['prices'][0].close
            price_change = ((last_price - first_price) / first_price) * 100
            price_summary = f"Price moved from {first_price:.2f} to {last_price:.2f} ({price_change:.2f}%)"
        else:
            price_summary = "No price data available."

        sentiment_summary = ""
        if data['news_sentiment']:
            pos = len([s for s in data['news_sentiment'] if s['sentiment'] == 'positive'])
            neg = len([s for s in data['news_sentiment'] if s['sentiment'] == 'negative'])
            sentiment_summary = f"News sentiment: {pos} positive, {neg} negative articles found."
        else:
            sentiment_summary = "No recent news available."

        filing_summary = f"Found {len(data['filings'])} recent SEC filings."

        prompt = (
            f"You are a professional financial analyst. Provide a concise research report for {ticker}.\n\n"
            f"Data gathered:\n"
            f"- Price Action: {price_summary}\n"
            f"- Sentiment: {sentiment_summary}\n"
            f"- Filings: {filing_summary}\n\n"
            f"Analyze the potential outlook for this stock based on this data. "
            f"Be objective and highlight both risks and opportunities."
        )

        try:
            logger.info(f"Requesting analysis from Ollama ({self.llm_model})...")
            response = ollama.generate(model=self.llm_model, prompt=prompt)
            return response['response']
        except Exception as e:
            logger.error(f"Error during LLM analysis: {e}")
            return f"Failed to generate analysis for {ticker} due to LLM error: {e}"
