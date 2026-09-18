import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add current directory to sys.path to handle imports
sys.path.append(os.getcwd())

# Mock config before importing models/agents to avoid DB connection errors
with patch('config.config.config.DATABASE_URL', 'sqlite:///:memory:'):
    from agents.research_agent import ResearchAgent
    from db.models import Price, NewsArticle

class TestResearchAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ResearchAgent()

    @patch('agents.research_agent.AlpacaClient')
    @patch('agents.research_agent.YFinanceClient')
    @patch('agents.research_agent.NewsClient')
    @patch('agents.research_agent.EdgarClient')
    @patch('agents.research_agent.SentimentScorer')
    def test_gather_data(self, mock_scorer, mock_edgar, mock_news, mock_yf, mock_alpaca):
        # Setup mocks
        mock_alpaca_inst = mock_alpaca.return_value
        mock_alpaca_inst.get_historical_prices.return_value = [
            Price(ticker='AAPL', timestamp=None, open=150.0, high=155.0, low=149.0, close=152.0, volume=1000),
            Price(ticker='AAPL', timestamp=None, open=152.0, high=157.0, low=151.0, close=155.0, volume=1100)
        ]
        
        mock_news_inst = mock_news.return_value
        mock_news_inst.fetch_news.return_value = [
            NewsArticle(article_id='1', ticker='AAPL', title='Apple Growth', content='Apple is growing fast', source='CNBC', published_at=None)
        ]
        
        mock_scorer_inst = mock_scorer.return_value
        # Mock SentimentScore object
        mock_score = MagicMock()
        mock_score.label = 'positive'
        mock_score.confidence = 0.95
        mock_scorer_inst.score_text.return_value = mock_score
        
        mock_edgar_inst = mock_edgar.return_value
        mock_edgar_inst.download_filings.return_value = [MagicMock()]

        # Execute
        data = self.agent.gather_data('AAPL')

        # Verify
        self.assertEqual(data['ticker'], 'AAPL')
        self.assertEqual(len(data['prices']), 2)
        self.assertEqual(len(data['news_sentiment']), 1)
        self.assertEqual(data['news_sentiment'][0]['sentiment'], 'positive')
        self.assertTrue(len(data['filings']) > 0)

    @patch('agents.research_agent.ollama.generate')
    @patch('agents.research_agent.ResearchAgent.gather_data')
    def test_analyze(self, mock_gather, mock_ollama):
        # Setup mocks
        mock_gather.return_value = {
            'ticker': 'AAPL',
            'prices': [
                Price(ticker='AAPL', timestamp=None, open=150.0, high=155.0, low=149.0, close=150.0, volume=1000),
                Price(ticker='AAPL', timestamp=None, open=152.0, high=157.0, low=151.0, close=160.0, volume=1100)
            ],
            'news_sentiment': [{'title': 'Good News', 'sentiment': 'positive', 'confidence': 0.9}],
            'filings': [MagicMock()],
            'start_date': '2023-01-01',
            'end_date': '2023-01-31'
        }
        
        mock_ollama.return_value = {'response': 'AAPL is a strong buy based on analysis.'}

        # Execute
        report = self.agent.analyze('AAPL')

        # Verify
        self.assertIn('AAPL is a strong buy', report)
        mock_ollama.assert_called_once()

if __name__ == '__main__':
    unittest.main()
