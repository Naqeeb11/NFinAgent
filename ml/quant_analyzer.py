import pandas as pd
import pandas_ta as ta
import logging
from typing import Dict, Any
from db.manager import DatabaseManager
from db.models import Price

logger = logging.getLogger(__name__)

class QuantAnalyzer:
    """
    Analyzes historical price data to extract technical indicators.
    """
    def __init__(self):
        self.db = DatabaseManager()

    def analyze_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieves price data from DB and calculates technical indicators.
        """
        try:
            # 1. Fetch price data from DB
            # We need at least 200 days for 200 SMA
            from db.models import SessionLocal
            session = SessionLocal()
            
            # Get last 200 records for the ticker
            prices_query = session.query(Price).filter_by(ticker=ticker).order_by(Price.timestamp.desc()).limit(200).all()
            session.close()

            if not prices_query:
                logger.warning(f"No price data found in DB for {ticker}")
                return {"error": "No price data available"}

            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': p.timestamp,
                'open': p.open,
                'high': p.high,
                'low': p.low,
                'close': p.close,
                'volume': p.volume
            } for p in prices_query])
            
            # Sort by timestamp ascending for TA calculations
            df = df.sort_values('timestamp')

            # 2. Calculate Indicators using pandas_ta
            # RSI
            df['RSI'] = ta.rsi(df['close'], length=14)
            
            # MACD
            macd = ta.macd(df['close'])
            # MACD returns a DF with MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            
            # SMA
            df['SMA_50'] = ta.sma(df['close'], length=50)
            df['SMA_200'] = ta.sma(df['close'], length=200)
            
            # ATR
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

            # Get the most recent values
            last_row = df.iloc[-1]
            
            # Extract MACD values safely
            macd_val = macd.iloc[-1] if macd is not None else {}

            summary = {
                'last_close': last_row['close'],
                'rsi': last_row['RSI'],
                'macd': macd_val.get('MACD_12_26_9', None),
                'macd_signal': macd_val.get('MACDs_12_26_9', None),
                'macd_hist': macd_val.get('MACDh_12_26_9', None),
                'sma_50': last_row['SMA_50'],
                'sma_200': last_row['SMA_200'],
                'atr': last_row['ATR'],
                'trend': 'Bullish' if last_row['close'] > last_row['SMA_50'] else 'Bearish'
            }

            # Clean NaN values for the LLM
            summary = {k: (round(v, 4) if isinstance(v, (float, int)) else v) 
                       for k, v in summary.items() if pd.notna(v)}

            return summary

        except Exception as e:
            logger.error(f"Error in QuantAnalyzer for {ticker}: {e}")
            return {"error": str(e)}
