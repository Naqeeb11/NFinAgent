import logging
from db.models import SentimentScore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentScorer:
    """
    Sentiment analysis module using FinBERT to score financial text.
    """
    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self):
        self._sentiment_pipeline = None

    @property
    def pipeline(self):
        """Lazy initialization of the transformer pipeline."""
        if self._sentiment_pipeline is None:
            try:
                from transformers import pipeline
                logger.info(f"Loading FinBERT model: {self.MODEL_NAME}...")
                self._sentiment_pipeline = pipeline(
                    "sentiment-analysis", 
                    model=self.MODEL_NAME, 
                    tokenizer=self.MODEL_NAME
                )
            except Exception as e:
                logger.error(f"Failed to load FinBERT model: {e}")
                raise e
        return self._sentiment_pipeline

    def score_text(self, text: str, article_id: int) -> SentimentScore:
        """
        Analyzes the sentiment of a given text and returns a SentimentScore model.
        """
        if not text or text.strip() == "":
            return SentimentScore(
                article_id=article_id,
                label="neutral",
                confidence=0.0,
                model_version=self.MODEL_NAME
            )

        try:
            # FinBERT handles texts up to 512 tokens. 
            # For longer texts, we truncate (simplification for this implementation).
            result = self.pipeline(text[:2000])[0]
            
            return SentimentScore(
                article_id=article_id,
                label=result['label'].lower(),
                confidence=result['score'],
                model_version=self.MODEL_NAME
            )
        except Exception as e:
            logger.error(f"Error scoring text for article {article_id}: {e}")
            # Fallback to neutral on error
            return SentimentScore(
                article_id=article_id,
                label="neutral",
                confidence=0.0,
                model_version=self.MODEL_NAME
            )