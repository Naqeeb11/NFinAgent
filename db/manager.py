import logging
import datetime
from typing import List, Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.models import (
    SessionLocal, Price, NewsArticle, SentimentScore,
    CompanyFiling, FilingChunk, ResearchReport, EMBEDDING_DIM,
)

logger = logging.getLogger(__name__)

# all-MiniLM-L6-v2's real limit is 256 tokens, noticeably shorter than
# nomic-embed-text's. 800 characters keeps chunks comfortably under that even
# for token-dense financial/legal text, so nothing gets silently truncated
# mid-sentence by the model itself.
CHUNK_SIZE_CHARS = 800
CHUNK_OVERLAP_CHARS = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    """Splits text into overlapping fixed-size character chunks."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return chunks


class EmbeddingManager:
    """
    Generates embeddings using sentence-transformers, running in-process
    rather than through Ollama's HTTP endpoint. This avoids the per-request
    network/model-loading overhead of the Ollama server and its context-length
    errors -- sentence-transformers truncates over-length input silently
    instead of erroring, and there's no HTTP round trip per chunk.
    """
    MODEL_NAME = "all-MiniLM-L6-v2"

    # Loaded once per process and shared across every EmbeddingManager
    # instance, since DatabaseManager (and therefore EmbeddingManager) gets
    # instantiated more than once (e.g. QuantAnalyzer has its own
    # DatabaseManager). Without this, the model would load from disk
    # repeatedly, which is exactly the kind of slowness we're trying to avoid.
    _model = None

    def __init__(self):
        if EmbeddingManager._model is None:
            logger.info(f"Loading embedding model: {self.MODEL_NAME}...")
            EmbeddingManager._model = SentenceTransformer(self.MODEL_NAME)
        self.model = EmbeddingManager._model

    def generate(self, text: str) -> Optional[List[float]]:
        """
        Returns an embedding vector, or None if the text is empty or embedding
        fails. Returning None instead of a zero vector matters: a zero vector
        has no direction, so cosine similarity against it is undefined and can
        silently corrupt search rankings.
        """
        if not text or not text.strip():
            return None
        try:
            embedding = self.model.encode(text, show_progress_bar=False)
            vector = embedding.tolist()
            if len(vector) != EMBEDDING_DIM:
                logger.error(
                    f"Unexpected embedding shape from {self.MODEL_NAME}: "
                    f"got {len(vector)}, expected {EMBEDDING_DIM}"
                )
                return None
            return vector
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def generate_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generates embeddings for a batch of texts. This is significantly faster than
        calling generate() in a loop because it leverages the model's internal
        vectorization.
        """
        if not texts:
            return []
        try:
            embeddings = self.model.encode(texts, show_progress_bar=False)
            results = []
            for emb in embeddings:
                vector = emb.tolist()
                if len(vector) != EMBEDDING_DIM:
                    logger.error(f"Unexpected embedding shape: got {len(vector)}, expected {EMBEDDING_DIM}")
                    results.append(None)
                else:
                    results.append(vector)
            return results
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [None] * len(texts)

class DatabaseManager:
    """
    High-level API for database operations to decouple business logic from SQLAlchemy.
    """
    def __init__(self):
        self.session_factory = SessionLocal
        self.embedding_manager = EmbeddingManager()

    def _get_session(self) -> Session:
        return self.session_factory()

    @staticmethod
    def _to_naive_utc(ts):
        if ts is not None and getattr(ts, 'tzinfo', None) is not None:
            if hasattr(ts, 'tz_convert'):  # pandas Timestamp
                ts = ts.tz_convert('UTC').tz_localize(None)
            else:  # stdlib datetime
                ts = ts.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return ts

    # --- Price Data (unchanged) ---
    def save_price_data(self, ticker: str, price_list: List[dict]):
        if not price_list:
            return
        session = self._get_session()
        try:
            rows = []
            for item in price_list:
                ts = item.get('Timestamp') or item.get('Date')
                if isinstance(ts, tuple):
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
            logger.error(f"Error saving price data: {e}")
            raise
        finally:
            session.close()

    # --- News & Sentiment ---
    def save_news_article(self, ticker: str, article_data: dict, sentiment: dict):
        """
        Saves a news article, its sentiment score, and its embedding.
        Safe to call repeatedly for the same article_id.
        """
        session = self._get_session()
        try:
            article_id = str(article_data.get('id', 'unknown'))
            article = session.query(NewsArticle).filter_by(article_id=article_id).first()

            if article is None:
                source_info = article_data.get('source')
                source_name = source_info.get('name', 'unknown') if isinstance(source_info, dict) else 'unknown'
                title = article_data.get('title', 'No Title')
                content = article_data.get('description') or article_data.get('content')

                # Embed title + content together so the vector reflects both,
                # since a headline alone is often too short to be meaningful.
                embed_source = f"{title}. {content}" if content else title
                embedding = self.embedding_manager.generate(embed_source)

                article = NewsArticle(
                    article_id=article_id,
                    ticker=ticker,
                    title=title,
                    content=content,
                    source=source_name,
                    published_at=article_data.get('publishedAt'),
                    embedding=embedding,  # may be None if embedding failed -- that's fine, filtered out in search
                )
                session.add(article)
                session.flush()

            model_version = sentiment.get('model', 'finbert-v1')
            existing_score = session.query(SentimentScore).filter_by(
                article_id=article.id, model_version=model_version
            ).first()
            if existing_score is None:
                score = SentimentScore(
                    article_id=article.id,
                    label=sentiment['label'],
                    confidence=float(sentiment['score']),
                    model_version=model_version,
                )
                session.add(score)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving news/sentiment: {e}")
            raise
        finally:
            session.close()

    def save_article_with_embedding(self, ticker: str, article_data: dict):
        """
        Thin wrapper for callers that don't have a sentiment score yet (e.g.
        bulk ingestion before a scoring pass runs). The embedding is now
        generated inside save_news_article unconditionally, so this does what
        its name always promised -- previously it didn't actually embed anything.
        """
        dummy_sentiment = {'label': 'neutral', 'score': 0.5, 'model': 'none'}
        self.save_news_article(ticker, article_data, dummy_sentiment)

    # --- SEC Filings ---
    def save_filing(
        self,
        ticker: str,
        filing_type: str,
        local_path: str,
        accession_number: str,
        filed_at: datetime.datetime,
        content: Optional[str] = None,
    ) -> Optional[CompanyFiling]:
        """
        Records filing metadata and, if `content` (the extracted filing text)
        is provided, splits it into chunks and embeds each one into FilingChunk.

        `content` is the full extracted text of the filing -- use
        EdgarClient.extract_text(local_path), or the `.extracted_content`
        attribute EdgarClient.download_filings() now attaches to each result.
        Passing local_path alone does NOT extract text for you.

        Safe to call repeatedly: replaces the chunks for a given
        accession_number rather than duplicating them on re-runs.
        """
        session = self._get_session()
        try:
            filing = session.query(CompanyFiling).filter_by(accession_number=accession_number).first()
            is_new_filing = filing is None

            if filing is None:
                filing = CompanyFiling(
                    ticker=ticker,
                    filing_type=filing_type,
                    local_path=local_path,
                    accession_number=accession_number,
                    filed_at=filed_at,
                )
                session.add(filing)
            else:
                filing.ticker = ticker
                filing.filing_type = filing_type
                filing.local_path = local_path
                filing.filed_at = filed_at
            session.flush()  # ensures filing.id exists for the chunks below

            existing_chunk_count = session.query(FilingChunk).filter_by(filing_id=filing.id).count()

            # A filing's content never changes once it's been filed with the
            # SEC (accession_number is permanent), so if we've already
            # chunked and embedded it, redoing that work on every run is pure
            # waste -- for a large 10-K that's hundreds of wasted embedding
            # calls, every single time you research the same ticker again.
            should_embed = content and (is_new_filing or existing_chunk_count == 0)

            if should_embed:
                session.query(FilingChunk).filter_by(filing_id=filing.id).delete()

                chunks = chunk_text(content)
                total_chunks = len(chunks)
                logger.info(f"Chunking and embedding filing {ticker} ({accession_number}): {total_chunks} chunks to process")

                # Process in batches for significant speedup
                batch_size = 32
                for i in range(0, total_chunks, batch_size):
                    batch_chunks = chunks[i : i + batch_size]
                    embeddings = self.embedding_manager.generate_batch(batch_chunks)

                    for j, (chunk, embedding) in enumerate(zip(batch_chunks, embeddings)):
                        chunk_idx = i + j
                        if embedding is None:
                            logger.warning(f"Skipping chunk {chunk_idx} for {accession_number}: embedding failed")
                            continue
                        session.add(FilingChunk(
                            filing_id=filing.id,
                            chunk_index=chunk_idx,
                            content=chunk,
                            embedding=embedding,
                        ))
                    
                    if (i + batch_size) % 100 < batch_size: # Log roughly every 100
                        logger.info(f"Processing chunks for {ticker} ({accession_number}): {min(i + batch_size, total_chunks)}/{total_chunks}")
            elif content and existing_chunk_count > 0:
                logger.info(
                    f"Skipping re-embedding for {accession_number}: "
                    f"already has {existing_chunk_count} chunks."
                )

            session.commit()
            return filing
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving filing: {e}")
            raise
        finally:
            session.close()

    # --- Research Reports (unchanged) ---
    def save_report(self, ticker: str, rating: str, content: str, model: str):
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
            logger.error(f"Error saving report: {e}")
            raise
        finally:
            session.close()

    def get_latest_report(self, ticker: str) -> Optional[ResearchReport]:
        session = self._get_session()
        try:
            return session.query(ResearchReport).filter_by(ticker=ticker).order_by(ResearchReport.report_date.desc()).first()
        finally:
            session.close()

    # --- Semantic Search ---
    def semantic_search_news(self, ticker: str, query: str, limit: int = 5) -> List[NewsArticle]:
        """Semantic search over news articles for a ticker."""
        session = self._get_session()
        try:
            query_embedding = self.embedding_manager.generate(query)
            if query_embedding is None:
                return []
            return (
                session.query(NewsArticle)
                .filter(NewsArticle.ticker == ticker, NewsArticle.embedding.isnot(None))
                .order_by(NewsArticle.embedding.op('<=>')(query_embedding))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error during news semantic search: {e}")
            return []
        finally:
            session.close()

    def semantic_search_filings(self, ticker: str, query: str, limit: int = 5) -> List[FilingChunk]:
        """
        Semantic search over filing chunks for a ticker. Returns FilingChunk
        rows -- each has .content (the matching excerpt) and .filing (the
        parent CompanyFiling, for filing_type/filed_at context) -- rather
        than whole filings, so results point to a specific relevant passage.
        """
        session = self._get_session()
        try:
            query_embedding = self.embedding_manager.generate(query)
            if query_embedding is None:
                return []
            return (
                session.query(FilingChunk)
                .join(CompanyFiling)
                .filter(CompanyFiling.ticker == ticker, FilingChunk.embedding.isnot(None))
                .order_by(FilingChunk.embedding.op('<=>')(query_embedding))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error during filing semantic search: {e}")
            return []
        finally:
            session.close()

    def semantic_search(self, ticker: str, query: str, limit: int = 5) -> List[NewsArticle]:
        """Backward-compatible alias for semantic_search_news, in case other
        code still calls the old name."""
        return self.semantic_search_news(ticker, query, limit)