import os
import logging
from typing import List, Tuple, Optional
from datetime import datetime
from sec_edgar_downloader import Downloader
from db.models import CompanyFiling
from config.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EdgarClient:
    """
    Client to fetch SEC filings (10-K, 10-Q) using sec-edgar-downloader.
    """
    def __init__(self):
        # SEC requires an email address as the first argument in the newer versions of sec-edgar-downloader
        # config.SEC_USER_AGENT should be just the email address, or we can split it.
        # Based on the error, it specifically wants the 'email_address'.
        self.dl = Downloader(config.SEC_COMPANY_NAME, config.SEC_CONTACT_EMAIL)

    def _find_local_path(self, ticker: str, filing_type: str) -> List[Tuple[str, str]]:
        """
        Scans the downloaded folder to find the file path and accession number.
        sec-edgar-downloader stores files in a nested structure: 
        sec-edgar-filename/company/filing_type/accession_number/full_filing.txt
        """
        results = []
        base_path = "sec-edgar-filings"
        company_path = os.path.join(base_path, ticker)
        type_path = os.path.join(company_path, filing_type)
        
        if not os.path.exists(type_path):
            return results

        # Each folder under filing_type is an accession number
        for accession_number in os.listdir(type_path):
            folder_path = os.path.join(type_path, accession_number)
            if os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    if file.endswith(".txt") or file.endswith(".html"):
                        full_path = os.path.join(folder_path, file)
                        results.append((full_path, accession_number))
        
        return results

    def download_filings(self, ticker: str, filing_type: str) -> List[CompanyFiling]:
        """
        Downloads filings for a ticker and returns a list of CompanyFiling models.
        """
        try:
            logger.info(f"Downloading {filing_type} for {ticker}...")
            # This downloads files to the local directory
            self.dl.get(filing_type, ticker, limit=5)
            
            files_found = self._find_local_path(ticker, filing_type)
            
            filings = []
            for local_path, accession in files_found:
                # Attempt to get filing date from the filesystem or metadata
                # For simplicity in this implementation, we use the current date or file mtime
                file_mtime = os.path.getmtime(local_path)
                filed_at = datetime.fromtimestamp(file_mtime)
                
                filings.append(CompanyFiling(
                    ticker=ticker,
                    filing_type=filing_type,
                    filed_at=filed_at,
                    local_path=local_path,
                    accession_number=accession
                ))
                
            return filings

        except Exception as e:
            logger.error(f"Edgar downloader error for {ticker}: {e}")
            return []