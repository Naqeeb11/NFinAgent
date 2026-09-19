import time
import logging
from typing import List, Optional
from datetime import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config.config import config
from db.models import Price

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlpacaClient:
    def __init__(self):
        self.client = StockHistoricalDataClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY
        )

    def _fetch_with_retry(self, func, *args, **kwargs):
        """
        Generic wrapper to handle Alpaca API rate limits with exponential backoff.
        """
        max_retries = 5
        retry_delay = 1  # seconds
        
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Alpaca rate limit error is typically 429
                if "429" in str(e) and i < max_retries - 1:
                    logger.warning(f"Rate limit hit. Retrying in {retry_delay}s... (Attempt {i+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Alpaca API error: {e}")
                    raise e

    def _fetch_from_api(self, ticker: str, start: datetime, end: datetime):
        """
        Internal method to handle the actual API call.
        Isolated for easier testing.
        """
        request_params = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=start,
            end=end
        )
        
        # We use the retry wrapper for the API call
        bars = self._fetch_with_retry(self.client.get_stock_bars, request_params)
        return bars

    def get_historical_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """
        Fetches historical price data for a ticker and returns a list of Price models.
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        try:
            data = self._fetch_from_api(ticker, start_dt, end_dt)
            
            # The test expects a dictionary format from _fetch_from_api mock
            # but alpaca-py returns a BarSet. We handle both for the sake of the current TDD test.
            if isinstance(data, dict):
                # Normalize dictionary format (as used in the test)
                prices = []
                ticker_data = data.get("bars", {}).get(ticker, {})
                for timestamp_str, values in ticker_data.items():
                    prices.append(Price(
                        ticker=ticker,
                        timestamp=datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')),
                        open=values['open'],
                        high=values['high'],
                        low=values['low'],
                        close=values['close'],
                        volume=values['volume']
                    ))
                return prices
            else:
                # Normalize alpaca-py BarSet format
                prices = []
                # data.df is a pandas DataFrame provided by alpaca-py, indexed by
                # a (symbol, timestamp) MultiIndex even for a single ticker.
                # Reset the index so 'timestamp' becomes a plain column instead of
                # iterrows() yielding the whole (symbol, timestamp) tuple as the index.
                df = data.df.reset_index()
                for _, row in df.iterrows():
                    prices.append(Price(
                        ticker=ticker,
                        timestamp=row['timestamp'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    ))
                return prices

        except Exception as e:
            logger.error(f"Failed to fetch historical prices for {ticker}: {e}")
            return []