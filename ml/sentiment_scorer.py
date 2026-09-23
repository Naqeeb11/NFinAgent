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
                    tokenizer=self.MODEL_NAME,
                    # Let the tokenizer truncate by actual token count (FinBERT's
                    # real limit), rather than slicing the raw string by character
                    # count beforehand. text[:2000] characters could still be well
                    # over 512 tokens for dense financial text, which either
                    # silently scored on partial garbage or could error depending
                    # on the transformers version -- this way truncation is
                    # correct and explicit instead of a guessed stand-in.
                    truncation=True,
                    max_length=512,
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
            # Pass the full text -- truncation=True/max_length=512 on the
            # pipeline itself now handles the length limit correctly.
            result = self.pipeline(text)[0]

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