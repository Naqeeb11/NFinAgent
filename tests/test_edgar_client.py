import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from data_ingestion.edgar_client import EdgarClient
from db.models import CompanyFiling

def test_download_filings_normalization():
    """
    Test that SEC filings are correctly normalized into CompanyFiling models.
    """
    ticker = "AAPL"
    filing_type = "10-K"
    
    client = EdgarClient()
    
    with patch('data_ingestion.edgar_client.DlEdgar') as mock_dl_class:
        mock_dl = MagicMock()
        # Mock the download method to return something that indicates success
        mock_dl.get_filings.return_value = True 
        mock_dl_class.return_value = mock_dl
        
        # We mock the internal path discovery logic
        with patch('data_ingestion.edgar_client.EdgarClient._find_local_path') as mock_find_path:
            mock_find_path.return_value = ("/tmp/sec-edgar/AAPL/10-K/filing.txt", "0000320193-23-000106")
            
            results = client.download_filings(ticker, filing_type)
            
            assert len(results) == 1
            filing = results[0]
            assert isinstance(filing, CompanyFiling)
            assert filing.ticker == ticker
            assert filing.filing_type == filing_type
            assert filing.local_path == "/tmp/sec-edgar/AAPL/10-K/filing.txt"
            assert filing.accession_number == "0000320193-23-000106"