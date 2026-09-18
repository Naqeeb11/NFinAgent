import logging
from typing import List
import yfinance as yf
from db.models import Price

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YFinanceClient:
    """
    Client to fetch historical market data using yfinance.
    Primarily used for backfilling missing data.
    """
    def get_historical_prices(self, ticker: str, start_date: str, end_date: str) -> List[Price]:
        """
        Fetches historical OHLCV data for a ticker and returns a list of Price models.
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            # yfinance history returns a pandas DataFrame
            df = ticker_obj.history(start=start_date, end=end_date)
            
            if df.empty:
                logger.info(f"No data found for {ticker} between {start_date} and {end_date}")
                return []

            prices = []
            for timestamp, row in df.iterrows():
                prices.append(Price(
                    ticker=ticker,
                    timestamp=timestamp.to_pydatetime(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                ))
            
            return prices

        except Exception as e:
            logger.error(f"yfinance error fetching data for {ticker}: {e}")
            return []