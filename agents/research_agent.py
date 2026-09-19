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
from db.manager import DatabaseManager


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
        self.db = DatabaseManager()
        self.llm_model = config.OLLAMA_MODEL


    def gather_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collects historical prices, news, and filings for a ticker.
        Saves all ingested data to the database for persistence.
        """
        logger.info(f"Gathering data for {ticker}...")
        
        # Dates for historical data (last 30 days)
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')

        # 1. Fetch & Save Price Data
        prices = self.alpaca_client.get_historical_prices(ticker, start_date, end_date)
        if not prices:
            logger.info(f"Alpaca returned no data for {ticker}, trying yfinance...")
            prices = self.yfinance_client.get_historical_prices(ticker, start_date, end_date)
        
        if prices:
            # Convert to list of dicts for DB manager
            price_data = [{
                'Timestamp': p.timestamp,
                'Open': p.open,
                'High': p.high,
                'Low': p.low,
                'Close': p.close,
                'Volume': p.volume
            } for p in prices]
            self.db.save_price_data(ticker, price_data)

        # 2. Fetch & Save News
        news = self.news_client.fetch_news(ticker)
        sentiment_summaries = []
        for article in news:
            score = self.sentiment_scorer.score_text(article.content, getattr(article, 'article_id', 0))
            
            # Save to DB
            self.db.save_news_article(
                ticker=ticker,
                article_data={
                    'id': getattr(article, 'article_id', 'unknown'),
                    'title': article.title,
                    'description': article.content,
                    'source': {'name': getattr(article, 'source', 'unknown')},
                    'publishedAt': article.published_at
                },
                sentiment={'label': score.label, 'score': score.confidence, 'model': 'finbert-v1'}
            )
            
            sentiment_summaries.append({
                'title': article.title,
                'sentiment': score.label,
                'confidence': score.confidence
            })

        # 3. Fetch & Save Filings
        filings_metadata = []
        for f_type in ['10-K', '10-Q']:
            filings = self.edgar_client.download_filings(ticker, f_type)
            for f in filings:
                self.db.save_filing(
                    ticker=ticker,
                    filing_type=f_type,
                    local_path=f.local_path,
                    accession_number=f.accession_number,
                    filed_at=f.filed_at
                )
                filings_metadata.append(f)

        return {
            'ticker': ticker,
            'prices': prices,
            'news_sentiment': sentiment_summaries,
            'filings': filings_metadata,
            'start_date': start_date,
            'end_date': end_date
        }


    def analyze(self, ticker: str) -> str:
        """
        Gather data and use Ollama to generate a research report.
        Saves the final report to the database.
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
            report_content = response['response']
            
            # Extract a simple rating if present (e.g., "Rating: Buy")
            rating = "Neutral"
            if "Buy" in report_content: rating = "Buy"
            elif "Sell" in report_content: rating = "Sell"
            
            # Save the final report to DB
            self.db.save_report(
                ticker=ticker,
                rating=rating,
                content=report_content,
                model=self.llm_model
            )
            
            return report_content
        except Exception as e:
            logger.error(f"Error during LLM analysis: {e}")
            return f"Failed to generate analysis for {ticker} due to LLM error: {e}"

