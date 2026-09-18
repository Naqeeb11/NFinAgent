import pytest
from unittest.mock import patch, MagicMock
from data_ingestion.yfinance_client import YFinanceClient
from db.models import Price
import pandas as pd

def test_get_historical_prices_normalization():
    """
    Test that yfinance data is correctly normalized into Price models.
    """
    # Mocking yfinance Ticker.history return value (a pandas DataFrame)
    mock_df = pd.DataFrame({
        'Open': [150.0],
        'High': [155.0],
        'Low': [149.0],
        'Close': [153.0],
        'Volume': [1000000]
    }, index=[pd.Timestamp('2023-01-01')])
    
    client = YFinanceClient()
    
    with patch('yfinance.Ticker') as mock_ticker_class:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_ticker_class.return_value = mock_ticker
        
        results = client.get_historical_prices("AAPL", "2023-01-01", "2023-01-01")
        
        assert len(results) == 1
        price = results[0]
        assert isinstance(price, Price)
        assert price.ticker == "AAPL"
        assert price.close == 153.0
        assert price.volume == 1000000