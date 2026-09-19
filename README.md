# FinAgent - Ingestion & Research Layer

This is the implementation of the FinAgent data ingestion and research agent layer, designed to provide an end-to-end pipeline from financial data gathering to LLM-powered research reports.

## 🚀 Current Status: Functional End-to-End Pipeline
The system has successfully implemented a "First Vertical Slice" that orchestrates multiple financial data sources to generate a comprehensive equity research brief.

### 🛠️ What's Implemented
- **Research Orchestration**: `ResearchAgent` coordinates the flow between data clients and the LLM.
- **Data Ingestion Clients**:
    - `YFinanceClient`: Fetches real-time and historical price action.
    - `NewsClient`: Aggregates latest financial news via NewsAPI.
    - `EdgarClient`: Downloads SEC filings (10-K, 10-Q) using `sec-edgar-downloader`.
    - `AlpacaClient`: Integrates with Alpaca for market data.
- **Intelligence Layer**:
    - `SentimentScorer`: Analyzes news sentiment to provide bullish/bearish tilts.
    - **LLM Integration**: Local integration with **Ollama (Llama 3.1)** for final report synthesis.
- **Execution Entry Point**: `run_research.py` provides a runnable script to execute the full pipeline for a given ticker.

### 📊 Sample Output
Running `python run_research.py` produces a structured research brief. 

**Example Report for NVDA:**
```text
**EQUITY RESEARCH BRIEF: NVIDIA Corp (NVDA)**
**Date:** May 22, 2024
**Rating:** Neutral/Cautious (Short-term)

### #1. Executive Summary
NVDA is currently experiencing low-volatility price consolidation. While the technical price action remains slightly positive, it is countered by a bearish tilt in news sentiment. The high frequency of SEC filings suggests significant internal corporate activity or insider movements that warrant close monitoring.

### #2. Data Analysis
* **Price Action: Bullish Bias (Marginal)**
    * **Movement:** +0.82% ($217.56 → $219.34)
    * **Analysis:** The stock is exhibiting stability. A gain of less than 1% indicates a lack of strong conviction from buyers or sellers...

* **Sentiment Analysis: Bearish Tilt**
    * **Ratio:** 26 Positive / 31 Negative
    * **Analysis:** News sentiment is leaning negative. In a high-growth stock like NVDA, negative sentiment often stems from concerns over valuation peaks...

* **Regulatory Filings: High Activity**
    * **Volume:** 10 recent SEC filings.
    * **Analysis:** A cluster of 10 filings in a short window typically indicates insider trading (Form 4s)...

### #3. Risk vs. Opportunity Matrix
| **Opportunities (Upside)** | **Risks (Downside)** |
| :--- | :--- |
| **Price Support:** The stock is holding its ground despite negative news... | **Sentiment Decay:** Negative news sentiment can trigger a momentum shift... |
| **Information Asymmetry:** High filing volume may reveal bullish insider accumulation not yet priced in. | **Overvaluation:** Bearish sentiment often correlates with a perception that the "AI trade" has reached a local top. |
| **Consolidation Breakout:** Low volatility often precedes a sharp move; a break above $220 could signal a new rally. | **Regulatory Pressure:** Increased SEC filings may relate to compliance or governance hurdles. |

### #4. Final Outlook
**Short-Term Outlook: Neutral.**
The narrow price gain is insufficient to override the negative sentiment trend. The primary driver for the next move will likely be the content of the 10 SEC filings.

**Recommendation:** 
Maintain current positions but avoid aggressive entry at this level. Monitor the filings for **insider selling** (Bearish) vs. **institutional accumulation** (Bullish). A confirmed break above $220 with a shift toward positive sentiment would upgrade the outlook to Bullish.
```

## Setup Instructions

### 1. Prerequisites
- **Python 3.11+**
- **PostgreSQL** with **TimescaleDB** extension installed.
- **Ollama** installed and running locally.

### 2. Model Setup
Pull the required model for the research agent:
```bash
ollama pull llama3.1:8b
```

### 3. Environment Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Fill in your API keys in the `.env` file:
   - `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`
   - `NEWS_API_KEY`
   - `SEC_USER_AGENT` (Must be a valid email address for SEC EDGAR access)

### 4. Installation
Install dependencies:
```bash
pip install -r requirements.txt
```

### 5. Database Setup
Ensure you have a database created and the TimescaleDB extension enabled:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

## Project Structure
- `/agents`: Research agent implementation (`research_agent.py`).
- `/data_ingestion`: Client modules (`yfinance_client.py`, `news_client.py`, `edgar_client.py`, `alpaca_client.py`).
- `/ml`: Intelligence modules (`sentiment_scorer.py`).
- `/db`: Database schemas and SQLAlchemy models.
- `/config`: Configuration management.
- `/tests`: Test suite for all modules.

## Development Workflow
This project follows **Test-Driven Development (TDD)**. Run tests using:
```bash
pytest
```

## Development Log

### 2026-09-19
- **Improved Database Support**: 
    - Enhanced `DatabaseManager` integration within the `ResearchAgent` to ensure stable persistence of ingested data.
    - Optimized the `Price` model schema and data insertion logic in `db/models.py` and `db/manager.py` for better alignment with TimescaleDB's hypertable requirements.
- **Stability Fixes**: Resolved import issues and refined session management in the database layer to improve the robustness of the research pipeline.
- **Verification**: Validated the end-to-end flow from data ingestion to LLM report generation using `run_research.py`.

