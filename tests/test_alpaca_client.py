import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from data_ingestion.alpaca_client import AlpacaClient
from db.models import Price

def test_get_historical_prices_normalization():
    """
    Test that Alpaca API responses are correctly normalized into Price models.
    """
    # Mocking the Alpaca API response
    mock_data = {
        "bars": {
            "AAPL": {
                "2023-01-01T00:00:00Z": {
                    "open": 150.0,
                    "high": 155.0,
                    "low": 149.0,
                    "close": 153.0,
                    "volume": 1000000
                }
            }
        }
    }
    
    client = AlpacaClient()
    
    with patch('data_ingestion.alpaca_client.AlpacaClient._fetch_from_api') as mock_fetch:
        mock_fetch.return_value = mock_data
        
        results = client.get_historical_prices("AAPL", "2023-01-01", "2023-01-01")
        
        assert len(results) == 1
        price = results[0]
        assert isinstance(price, Price)
        assert price.ticker == "AAPL"
        assert price.close == 153.0
        assert price.volume == 1000000