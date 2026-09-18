import pytest
from unittest.mock import patch, MagicMock
from ml.sentiment_scorer import SentimentScorer
from db.models import SentimentScore

def test_score_sentiment_normalization():
    """
    Test that FinBERT output is correctly normalized into SentimentScore models.
    """
    text = "Apple reported record-breaking quarterly earnings, exceeding all analyst expectations."
    article_id = 123
    
    scorer = SentimentScorer()
    
    # Mocking the Hugging Face pipeline
    with patch('ml.sentiment_scorer.pipeline') as mock_pipeline:
        mock_pipe = MagicMock()
        # FinBERT pipeline returns a list of lists: [[{'label': 'positive', 'score': 0.99}]]
        mock_pipe.return_value = [[{'label': 'positive', 'score': 0.99}]]
        mock_pipeline.return_value = mock_pipe
        
        result = scorer.score_text(text, article_id)
        
        assert isinstance(result, SentimentScore)
        assert result.article_id == article_id
        assert result.label == "positive"
        assert result.confidence == 0.99
        assert result.model_version == "ProsusAI/finbert"