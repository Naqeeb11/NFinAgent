import logging
import re
import ollama
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from data_ingestion.alpaca_client import AlpacaClient
from data_ingestion.yfinance_client import YFinanceClient
from data_ingestion.edgar_client import EdgarClient
from data_ingestion.news_client import NewsClient
from ml.sentiment_scorer import SentimentScorer
from ml.quant_analyzer import QuantAnalyzer

from config.config import config
from db.manager import DatabaseManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tools the LLM can request during the reasoning loop, with a short
# description shown to the model so it knows when/how to call each one.
TOOL_DESCRIPTIONS = {
    "fetch_specific_news": "Search news for a specific concern, e.g. 'lawsuits' or 'supply chain'. ARGS: a short search query.",
    "fetch_filing_section": "Pull a section from the latest 10-K/10-Q filing, e.g. 'Risk Factors'. ARGS: the section name.",
    "get_quant_metrics": "Get technical/quantitative indicators (SMA, RSI, etc). ARGS: none.",
}

MAX_REASONING_ITERATIONS = 3


class ResearchAgent:
    """
    ResearchAgent integrates multiple data sources and an LLM to provide
    comprehensive financial research and analysis for a given ticker.

    analyze() runs a planning + tool-calling reasoning loop: the LLM sees an
    initial data summary, decides whether it needs more specific information,
    calls one of a small set of tools if so, and repeats (up to
    MAX_REASONING_ITERATIONS times) before writing the final report.
    """
    def __init__(self):
        self.alpaca_client = AlpacaClient()
        self.yfinance_client = YFinanceClient()
        self.edgar_client = EdgarClient()
        self.news_client = NewsClient()
        self.sentiment_scorer = SentimentScorer()
        self.db = DatabaseManager()
        self.quant_analyzer = QuantAnalyzer()

        self.llm_model = config.OLLAMA_MODEL

    # ------------------------------------------------------------------
    # Data gathering (unchanged pipeline: prices, news+sentiment, filings)
    # ------------------------------------------------------------------
    def gather_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collects historical prices, news, and filings for a ticker.
        Saves all ingested data to the database for persistence.
        """
        logger.info(f"Gathering data for {ticker}...")

        # Dates for historical data (last 300 days to support 200-day SMA)
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=300)).strftime('%Y-%m-%d')

        # 1. Fetch & Save Price Data
        prices = self.alpaca_client.get_historical_prices(ticker, start_date, end_date)
        if not prices:
            logger.info(f"Alpaca returned no data for {ticker}, trying yfinance...")
            prices = self.yfinance_client.get_historical_prices(ticker, start_date, end_date)

        if prices:
            price_data = [{
                'Timestamp': p.timestamp,
                'Open': p.open,
                'High': p.high,
                'Low': p.low,
                'Close': p.close,
                'Volume': p.volume
            } for p in prices]
            self.db.save_price_data(ticker, price_data)

        # 2. Fetch & Save News
        news = self.news_client.fetch_news(ticker)
        sentiment_summaries = []
        for article in news:
            score = self.sentiment_scorer.score_text(article.content, getattr(article, 'article_id', 0))

            self.db.save_news_article(
                ticker=ticker,
                article_data={
                    'id': getattr(article, 'article_id', 'unknown'),
                    'title': article.title,
                    'description': article.content,
                    'source': {'name': getattr(article, 'source', 'unknown')},
                    'publishedAt': article.published_at
                },
                # Use the sentiment scorer's own model name rather than a
                # hardcoded string, so the audit trail actually reflects
                # which model produced this score -- this matters a lot
                # for a project whose whole point is tracking that.
                sentiment={'label': score.label, 'score': score.confidence, 'model': score.model_version}
            )

            sentiment_summaries.append({
                'title': article.title,
                'sentiment': score.label,
                'confidence': score.confidence
            })

        # 3. Fetch & Save Filings
        filings_metadata = []
        for f_type in ['10-K', '10-Q']:
            filings = self.edgar_client.download_filings(ticker, f_type)
            for f in filings:
                self.db.save_filing(
                    ticker=ticker,
                    filing_type=f_type,
                    local_path=f.local_path,
                    accession_number=f.accession_number,
                    filed_at=f.filed_at,
                    # This was missing: without it, save_filing has nothing
                    # to chunk/embed and filing_chunks stays empty forever.
                    content=getattr(f, 'extracted_content', None),
                )
                filings_metadata.append(f)

        return {
            'ticker': ticker,
            'prices': prices,
            'news_sentiment': sentiment_summaries,
            'filings': filings_metadata,
            'start_date': start_date,
            'end_date': end_date
        }

    # ------------------------------------------------------------------
    # Tools the reasoning loop can call. Each takes only the args the LLM
    # should supply; `ticker` is bound via closures in analyze().
    # ------------------------------------------------------------------
    def fetch_specific_news(self, ticker: str, query: str) -> str:
        """Tool: Fetch news articles based on a specific query for a ticker."""
        logger.info(f"Agent tool: Fetching specific news for {ticker} with query: {query}")
        try:
            articles = self.news_client.search_news(ticker, query, limit=3)
            if not articles:
                return "No specific news found for this query."

            results = [f"Title: {a.title}\nContent: {a.content}" for a in articles]
            return "\n\n".join(results)
        except Exception as e:
            return f"Error fetching specific news: {e}"

    def fetch_filing_section(self, ticker: str, section_name: str) -> str:
        """Tool: Search for a specific section in the latest SEC filings."""
        logger.info(f"Agent tool: Searching filing section '{section_name}' for {ticker}")
        try:
            for f_type in ["10-K", "10-Q"]:
                files = self.edgar_client._find_local_path(ticker, f_type)
                if not files:
                    continue

                latest_file, _ = files[-1]
                # Use extract_text() rather than a raw read so HTML tags are
                # stripped first -- otherwise the section-boundary regex below
                # is searching text still full of markup, which can break the
                # match or return tag soup mixed into the excerpt.
                content = self.edgar_client.extract_text(latest_file)

                pattern = re.compile(
                    rf"{re.escape(section_name)}.*?(?=\n\s*ITEM|\n\s*Part|\Z)",
                    re.IGNORECASE | re.DOTALL
                )
                match = pattern.search(content)
                if match:
                    return match.group(0)[:3000] + "... [truncated]"

            return f"Could not find section '{section_name}' in latest 10-K or 10-Q filings."
        except Exception as e:
            return f"Error reading filing section: {e}"

    def get_quant_metrics(self, ticker: str) -> str:
        """Tool: Returns formatted quantitative/technical indicators for a ticker."""
        quant_data = self.quant_analyzer.analyze_ticker(ticker)
        if "error" not in quant_data:
            q_lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in quant_data.items()]
            return "\n".join(q_lines)
        return f"No quantitative indicators available: {quant_data.get('error')}"

    # ------------------------------------------------------------------
    # Planning + tool-calling reasoning loop
    # ------------------------------------------------------------------
    def _build_tool_dispatch(self, ticker: str) -> Dict[str, Any]:
        """Binds `ticker` into each tool so the LLM only supplies its own args."""
        return {
            "fetch_specific_news": lambda args: self.fetch_specific_news(ticker, args.strip()),
            "fetch_filing_section": lambda args: self.fetch_filing_section(ticker, args.strip()),
            "get_quant_metrics": lambda args: self.get_quant_metrics(ticker),
        }

    def _planning_prompt(self, ticker: str, context: str) -> str:
        tool_list = "\n".join(f"- {name}: {desc}" for name, desc in TOOL_DESCRIPTIONS.items())
        return (
            f"You are a financial analyst investigating {ticker}. Here is what you know so far:\n\n"
            f"{context}\n\n"
            f"Available tools:\n{tool_list}\n\n"
            f"Decide if you need more specific information before writing your final report.\n"
            f"Respond with EXACTLY ONE of the following formats, nothing else:\n"
            f"ACTION: <tool_name>\nARGS: <argument text, or 'none'>\n\n"
            f"or, if you have enough information:\n"
            f"FINAL: <one-sentence reason no more research is needed>"
        )

    def _parse_planning_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """Returns {'tool': name, 'args': args} if an ACTION was requested, else None for FINAL."""
        action_match = re.search(r"ACTION:\s*(\w+)\s*\n\s*ARGS:\s*(.*)", response_text, re.IGNORECASE)
        if action_match:
            tool_name = action_match.group(1).strip()
            args = action_match.group(2).strip()
            if tool_name in TOOL_DESCRIPTIONS:
                return {"tool": tool_name, "args": args}
            logger.warning(f"Planner requested unknown tool '{tool_name}'; treating as FINAL.")
        return None

    def _run_reasoning_loop(self, ticker: str, initial_summary: str) -> str:
        """
        Iteratively lets the LLM request tools to fill in gaps in the initial
        summary, up to MAX_REASONING_ITERATIONS times. Returns the accumulated
        context (initial summary + any tool results) ready for final synthesis.
        """
        context = initial_summary
        tool_dispatch = self._build_tool_dispatch(ticker)

        for iteration in range(MAX_REASONING_ITERATIONS):
            planning_prompt = self._planning_prompt(ticker, context)
            try:
                logger.info(f"Planning iteration {iteration + 1}/{MAX_REASONING_ITERATIONS} for {ticker}...")
                response = ollama.generate(model=self.llm_model, prompt=planning_prompt)
                decision_text = response['response']
            except Exception as e:
                logger.error(f"Planning step failed, proceeding to final report: {e}")
                break

            action = self._parse_planning_response(decision_text)
            if action is None:
                logger.info(f"Planner decided no more tools needed at iteration {iteration + 1}.")
                break

            tool_fn = tool_dispatch[action["tool"]]
            try:
                tool_result = tool_fn(action["args"])
            except Exception as e:
                tool_result = f"Tool '{action['tool']}' failed: {e}"

            context += (
                f"\n\n--- Tool call: {action['tool']}({action['args']}) ---\n"
                f"{tool_result}"
            )

        return context

    # ------------------------------------------------------------------
    # Final report generation
    # ------------------------------------------------------------------
    def analyze(self, ticker: str) -> str:
        """
        Gathers data, runs the planning + tool-calling reasoning loop to fill
        in any gaps, then uses Ollama to generate a structured Markdown
        research report. Saves the final report to the database.
        """
        data = self.gather_data(ticker)

        # Price summary
        if data['prices']:
            last_price = data['prices'][-1].close
            first_price = data['prices'][0].close
            price_change = ((last_price - first_price) / first_price) * 100
            price_summary = f"Price moved from {first_price:.2f} to {last_price:.2f} ({price_change:.2f}%)"
        else:
            price_summary = "No price data available."

        # Quantitative summary
        quant_data = self.quant_analyzer.analyze_ticker(ticker)
        if "error" not in quant_data:
            quant_summary = "\n".join(
                f"{k.replace('_', ' ').title()}: {v}" for k, v in quant_data.items()
            )
        else:
            quant_summary = "No quantitative indicators available."

        # Sentiment summary
        if data['news_sentiment']:
            pos = len([s for s in data['news_sentiment'] if s['sentiment'] == 'positive'])
            neg = len([s for s in data['news_sentiment'] if s['sentiment'] == 'negative'])
            sentiment_summary = f"News sentiment: {pos} positive, {neg} negative articles found."
        else:
            sentiment_summary = "No recent news available."

        filing_summary = f"Found {len(data['filings'])} recent SEC filings."

        initial_summary = (
            f"- Price Action: {price_summary}\n"
            f"- Quantitative Data:\n{quant_summary}\n"
            f"- Sentiment: {sentiment_summary}\n"
            f"- Filings: {filing_summary}"
        )

        # Planning + tool-calling loop: may enrich `enriched_context` with
        # targeted news searches, filing sections, or quant re-checks.
        enriched_context = self._run_reasoning_loop(ticker, initial_summary)

        final_prompt = (
            f"You are a professional financial analyst. Using all the research below "
            f"(including any follow-up investigation), write a concise research report "
            f"for {ticker} in structured Markdown, with headers for Price Action, "
            f"Quantitative Analysis, Sentiment, Filings, and Outlook.\n\n"
            f"Research gathered:\n{enriched_context}\n\n"
            f"Be objective and highlight both risks and opportunities. "
            f"End with a clear Rating: Buy, Hold, or Sell."
        )

        try:
            logger.info(f"Requesting final report from Ollama ({self.llm_model})...")
            response = ollama.generate(model=self.llm_model, prompt=final_prompt)
            report_content = response['response']

            rating = "Hold"
            if "Buy" in report_content:
                rating = "Buy"
            elif "Sell" in report_content:
                rating = "Sell"

            self.db.save_report(
                ticker=ticker,
                rating=rating,
                content=report_content,
                model=self.llm_model
            )

            return report_content
        except Exception as e:
            logger.error(f"Error during LLM analysis: {e}")
            return f"Failed to generate analysis for {ticker} due to LLM error: {e}"