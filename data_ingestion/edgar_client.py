import os
import re
import logging
from typing import List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from sec_edgar_downloader import Downloader
from db.models import CompanyFiling
from config.config import config

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r'\s+')


class EdgarClient:
    """
    Client to fetch SEC filings (10-K, 10-Q) using sec-edgar-downloader.
    """
    def __init__(self):
        self.dl = Downloader(config.SEC_COMPANY_NAME, config.SEC_CONTACT_EMAIL)

    def _find_local_path(self, ticker: str, filing_type: str) -> List[Tuple[str, str]]:
        """
        Scans the downloaded folder to find the the most recent filing path and accession number.
        sec-edgar-downloader stores files in a nested structure:
        sec-edgar-filings/company/filing_type/accession_number/full_filing.txt
        """
        base_path = "sec-edgar-filings"
        company_path = os.path.join(base_path, ticker)
        type_path = os.path.join(company_path, filing_type)

        if not os.path.exists(type_path):
            return []

        # Gather all candidates first
        candidates = []
        for accession_number in os.listdir(type_path):
            folder_path = os.path.join(type_path, accession_number)
            if os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    if file.endswith(".txt") or file.endswith(".html") or file.endswith(".htm"):
                        full_path = os.path.join(folder_path, file)
                        # Use file mtime as a proxy for filed_at
                        mtime = os.path.getmtime(full_path)
                        candidates.append((full_path, accession_number, mtime))

        # Sort by mtime descending so the most recent filing is first
        candidates.sort(key=lambda x: x[2], reverse=True)

        # Return only (path, accession) for compatibility
        return [(c[0], c[1]) for c in candidates]

    def extract_text(self, local_path: str) -> str:
        """
        Reads a downloaded filing file and returns clean, readable plain text.

        Modern SEC filings are Inline XBRL HTML documents that routinely embed
        large <script>/<style> blocks -- often thousands of characters with NO
        whitespace (minified JS, XBRL viewer data). A naive tag-stripping regex
        removes the <script> wrapper but leaves that content behind as one giant
        "word" with no spaces, which then blows up any word-count-based chunking
        downstream (a single such blob can push a whole chunk's real token count
        far past the embedding model's context limit). BeautifulSoup lets us
        drop script/style CONTENT entirely, not just the tags, and its
        get_text(separator=' ') correctly inserts a space at every element
        boundary so words from adjacent tags don't get glued together either.
        """
        try:
            with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw = f.read()
        except OSError as e:
            logger.error(f"Could not read filing file {local_path}: {e}")
            return ""

        if local_path.lower().endswith(('.html', '.htm')):
            soup = BeautifulSoup(raw, 'html.parser')
            # Remove script/style (and head, which can contain metadata/XBRL
            # blobs too) COMPLETELY -- decompose() removes the tag AND its
            # content, unlike a regex that only matches the tag itself.
            for tag in soup(['script', 'style', 'head']):
                tag.decompose()
            text = soup.get_text(separator=' ')
        else:
            text = raw

        text = _WHITESPACE_RE.sub(' ', text).strip()
        
        # To reduce processing time (embedding/chunking), only return the first 1/4 of the document.
        # This usually captures the most critical summary sections and financial highlights.
        return text[:len(text) // 4]

    def download_filings(self, ticker: str, filing_type: str) -> List[CompanyFiling]:
        """
        Downloads filings for a ticker and returns a list of CompanyFiling
        models. Each returned object also carries an `.extracted_content`
        attribute (not a DB column -- just in-memory) so the caller can pass
        real text straight into db_manager.save_filing(content=...) without
        a second disk read.
        """
        try:
            logger.info(f"Downloading {filing_type} for {ticker}...")
            # Reduced from 5 to 1: each additional filing can mean hundreds of
            # more embedding calls on a slow first run.
            limit = 1
            logger.info(f"Requesting {limit} filing(s) for {ticker}. This will result in approximately {limit} download operation(s).")
            self.dl.get(filing_type, ticker, limit=limit)

            files_found = self._find_local_path(ticker, filing_type)

            filings = []
            for local_path, accession in files_found:
                file_mtime = os.path.getmtime(local_path)
                filed_at = datetime.fromtimestamp(file_mtime)

                filing = CompanyFiling(
                    ticker=ticker,
                    filing_type=filing_type,
                    filed_at=filed_at,
                    local_path=local_path,
                    accession_number=accession,
                )
                filing.extracted_content = self.extract_text(local_path)
                filings.append(filing)

            return filings

        except Exception as e:
            logger.error(f"Edgar downloader error for {ticker}: {e}")
            return []