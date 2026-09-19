from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from db.models import SessionLocal, Price, NewsArticle, SentimentScore, CompanyFiling, ResearchReport
from typing import List, Optional
import datetime

class DatabaseManager:
    """
    High-level API for database operations to decouple business logic from SQLAlchemy.
    """
    def __init__(self):
        self.session_factory = SessionLocal

    def _get_session(self) -> Session:
        return self.session_factory()

    @staticmethod
    def _to_naive_utc(ts):
        """
        Normalize a timestamp to naive UTC so it matches the
        'timestamp without time zone' column and compares/upserts consistently.
        """
        if ts is not None and getattr(ts, 'tzinfo', None) is not None:
            if hasattr(ts, 'tz_convert'):  # pandas Timestamp
                ts = ts.tz_convert('UTC').tz_localize(None)
            else:  # stdlib datetime
                ts = ts.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return ts

    # --- Price Data ---
    def save_price_data(self, ticker: str, price_list: List[dict]):
        """
        Upserts a list of price records into the TimescaleDB hypertable.
        Uses INSERT ... ON CONFLICT DO UPDATE on (timestamp, ticker) so
        re-running for overlapping dates updates existing rows instead of
        raising a duplicate-key error.
        """
        if not price_list:
            return

        session = self._get_session()
        try:
            rows = []
            for item in price_list:
                # Handle both Timestamp (datetime) and Date keys
                ts = item.get('Timestamp') or item.get('Date')
                if isinstance(ts, tuple):  # defensive: guard against stray (symbol, ts) tuples
                    ts = ts[-1]
                ts = self._to_naive_utc(ts)

                rows.append({
                    'timestamp': ts,
                    'ticker': ticker,
                    'open': float(item.get('Open', 0)),
                    'high': float(item.get('High', 0)),
                    'low': float(item.get('Low', 0)),
                    'close': float(item.get('Close', 0)),
                    'volume': float(item.get('Volume', 0)),
                })

            stmt = pg_insert(Price).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=['timestamp', 'ticker'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                },
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving price data: {e}")
            raise e
        finally:
            session.close()

    # --- News & Sentiment ---
    def save_news_article(self, ticker: str, article_data: dict, sentiment: dict):
        """Saves news article and its associated sentiment score.
        Safe to call repeatedly for the same article_id: skips re-inserting
        the article and re-scoring sentiment if both already exist."""
        session = self._get_session()
        try:
            article_id = str(article_data.get('id', 'unknown'))

            # 1. Save Article (or reuse existing one)
            article = session.query(NewsArticle).filter_by(article_id=article_id).first()
            if article is None:
                source_info = article_data.get('source')
                source_name = source_info.get('name', 'unknown') if isinstance(source_info, dict) else 'unknown'

                article = NewsArticle(
                    article_id=article_id,
                    ticker=ticker,
                    title=article_data.get('title', 'No Title'),
                    content=article_data.get('description') or article_data.get('content'),
                    source=source_name,
                    published_at=article_data.get('publishedAt')
                )
                session.add(article)
                session.flush() # Get article.id

            # 2. Save Sentiment, skipping if this article/model was already scored
            model_version = sentiment.get('model', 'finbert-v1')
            existing_score = session.query(SentimentScore).filter_by(
                article_id=article.id, model_version=model_version
            ).first()
            if existing_score is None:
                score = SentimentScore(
                    article_id=article.id,
                    label=sentiment['label'],
                    confidence=float(sentiment['score']),
                    model_version=model_version
                )
                session.add(score)

            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving news/sentiment: {e}")
            raise e
        finally:
            session.close()

    # --- SEC Filings ---
    def save_filing(self, ticker: str, filing_type: str, local_path: str, accession_number: str, filed_at: datetime.datetime):
        """Records the local path and metadata of a downloaded SEC filing.
        Safe to call repeatedly for the same accession_number: updates the
        existing row instead of raising a duplicate-key error."""
        session = self._get_session()
        try:
            filing = session.query(CompanyFiling).filter_by(accession_number=accession_number).first()
            if filing is None:
                filing = CompanyFiling(
                    ticker=ticker,
                    filing_type=filing_type,
                    local_path=local_path,
                    accession_number=accession_number,
                    filed_at=filed_at
                )
                session.add(filing)
            else:
                filing.ticker = ticker
                filing.filing_type = filing_type
                filing.local_path = local_path
                filing.filed_at = filed_at
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving filing: {e}")
            raise e
        finally:
            session.close()

    # --- Research Reports ---
    def save_report(self, ticker: str, rating: str, content: str, model: str):
        """Stores the final generated research report."""
        session = self._get_session()
        try:
            report = ResearchReport(
                ticker=ticker,
                rating=rating,
                content=content,
                model_used=model
            )
            session.add(report)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving report: {e}")
            raise e
        finally:
            session.close()

    def get_latest_report(self, ticker: str) -> Optional[ResearchReport]:
        """Retrieves the most recent report for a ticker."""
        session = self._get_session()
        try:
            return session.query(ResearchReport).filter_by(ticker=ticker).order_by(ResearchReport.report_date.desc()).first()
        finally:
            session.close()