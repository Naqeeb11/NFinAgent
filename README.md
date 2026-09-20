# FinAgent - Ingestion & Research Layer

This is the implementation of the FinAgent data ingestion and research agent layer, designed to provide an end-to-end pipeline from financial data gathering to LLM-powered research reports.

## ?? Current Status: Agentic Research Pipeline

The system has transitioned from a linear data pipeline to an **Agentic Reasoning Loop**. The ResearchAgent now acts as an autonomous analyst that can decide which tools to call to deepen its research before finalizing a report.

### ??? What's Implemented

- **Agentic Reasoning Loop**: ResearchAgent now implements a " Plan $\rightarrow$ Execute $\rightarrow$ Observe\ loop. Instead of a single LLM call, it can iteratively gather information using tools.
- **Tool-Calling Capabilities**:
- etch_specific_news(query): Targeted search for specific news topics (e.g., \lawsuits\, \product launches\).
- etch_filing_section(section): Targeted extraction of SEC filing sections (e.g., \Risk Factors\).
- get_quant_metrics(): On-demand refresh of technical indicators.
- **Data Ingestion Clients**:
- YFinanceClient: Fetches real-time and historical price action.
- NewsClient: Aggregates latest financial news via NewsAPI.
- EdgarClient: Downloads SEC filings (10-K, 10-Q) using sec-edgar-downloader.
- AlpacaClient: Integrates with Alpaca for market data.
- **Intelligence Layer**:
- SentimentScorer: Analyzes news sentiment to provide bullish/bearish tilts.
- **LLM Integration**: Local integration with **Ollama (Llama 3.1)** for multi-step reasoning and report synthesis.
- **Execution Entry Point**:
  un_research.py provides a runnable script to execute the full pipeline for a given ticker.

### ?? Sample Output

Running python run_research.py produces a structured research brief. The agent may now perform multiple \thought steps\ before outputting the final report.

**Example Report for NVDA:**
` ext
**EQUITY RESEARCH BRIEF: NVIDIA Corp (NVDA)**
**Date:** May 22, 2024
**Rating:** Neutral/Cautious (Short-term)

### #1. Executive Summary

NVDA is currently experiencing low-volatility price consolidation. While the technical price action remains slightly positive, it is countered by a bearish tilt in news sentiment. The high frequency of SEC filings suggests significant internal corporate activity or insider movements that warrant close monitoring.

### #2. Data Analysis

- **Price Action: Bullish Bias (Marginal)**
- **Movement:** +0.82% (.56 ? .34)
- **Analysis:** The stock is exhibiting stability. A gain of less than 1% indicates a lack of conviction...

- **Sentiment Analysis: Bearish Tilt**
- **Ratio:** 26 Positive / 31 Negative
- **Analysis:** News sentiment is leaning negative...

- **Regulatory Filings: High Activity**
- **Volume:** 10 recent SEC filings.
- **Analysis:** A cluster of 10 filings in a short window typically indicates insider trading...

### #3. Risk vs. Opportunity Matrix

| **Opportunities (Upside)**                            | **Risks (Downside)**                            |
| :---------------------------------------------------- | :---------------------------------------------- |
| **Price Support:** The stock is holding its ground... | **Sentiment Decay:** Negative news sentiment... |
| **Information Asymmetry:** High filing volume...      | **Overvaluation:** Bearish sentiment...         |

### #4. Final Outlook

**Short-Term Outlook: Neutral.**
The narrow price gain is insufficient to override the negative sentiment trend.
``n

## Setup Instructions

### 1. Prerequisites

- **Python 3.11+**
- **PostgreSQL** with **TimescaleDB** extension installed.
- **Ollama** installed and running locally.

### 2. Model Setup

Pull the required model for the research agent:
`ash
ollama pull llama3.1:8b
``n

### 3. Environment Configuration

1. Copy the example environment file:
   `ash
   cp .env.example .env
   ``n2. Fill in your API keys in the .env file:

- ALPACA_API_KEY / ALPACA_SECRET_KEY`n - NEWS_API_KEY`n - SEC_USER_AGENT (Must be a valid email address for SEC EDGAR access)

### 4. Installation

Install dependencies:
`ash
pip install -r requirements.txt
``n

### 5. Database Setup

Ensure you have a database created and the TimescaleDB extension enabled:
`sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
``n

## Project Structure

- /agents: Research agent implementation (
  esearch_agent.py).
- /data_ingestion: Client modules (yfinance_client.py,
  ews_client.py, edgar_client.py, lpaca_client.py).
- /ml: Intelligence modules (sentiment_scorer.py).
- /db: Database schemas and SQLAlchemy models.
- /config: Configuration management.
- /tests: Test suite for all modules.

## Development Workflow

This project follows **Test-Driven Development (TDD)**. Run tests using:
`ash
pytest
``n

## Development Log

### 2026-09-20

- **Refactored ResearchAgent to Agentic Loop**:
- Transitioned nalyze() from a linear pipeline to a multi-step reasoning loop (Plan $\rightarrow$ Execute $\rightarrow$ Observe).
- Implemented tool-calling syntax (TOOL: tool_name(\arg\)) allowing the LLM to request specific news or SEC filing sections on-demand.
- Integrated tool handlers for etch_specific_news, etch_filing_section, and get_quant_metrics.
- Added iteration capping and fallback reporting to ensure termination.

### 2026-09-19

- **Improved Database Support**:
- Enhanced DatabaseManager integration within the ResearchAgent to ensure stable persistence of ingested data.
- Optimized the Price model schema and data insertion logic in db/models.py and db/manager.py for better alignment with TimescaleDB's hypertable requirements.
- **Stability Fixes**: Resolved import issues and refined session management in the database layer to improve the robustness of the research pipeline.
- **Verification**: Validated the end-to-end flow from data ingestion to LLM report generation using
  un_research.py.

# FinAgent - Ingestion & Research Layer

This is the implementation of the FinAgent data ingestion and research agent layer, designed to provide an end-to-end pipeline from financial data gathering to LLM-powered research reports.

## Current Status: Agentic Research Pipeline

The system has transitioned from a linear data pipeline to an **Agentic Reasoning Loop**. The ResearchAgent now acts as an autonomous analyst that can decide which tools to call to deepen its research before finalizing a report.

### What's Implemented

- **Agentic Reasoning Loop**: ResearchAgent now implements a "Plan → Execute → Observe" loop. Instead of a single LLM call, it iteratively gathers information using tools before writing the final report (capped at 3 iterations, with a fallback straight to reporting if planning fails).
- **Tool-Calling Capabilities**:
   - `fetch_specific_news(query)`: Targeted search for specific news topics (e.g., "lawsuits", "product launches").
   - `fetch_filing_section(section)`: Targeted extraction of SEC filing sections (e.g., "Risk Factors").
   - `get_quant_metrics()`: On-demand refresh of technical indicators.
- **Data Ingestion Clients**:
   - `AlpacaClient`: Primary source for historical price bars.
   - `YFinanceClient`: Fallback for historical price action when Alpaca returns no data.
   - `NewsClient`: Aggregates latest financial news via NewsAPI, with both a general `fetch_news(ticker)` and a targeted `search_news(ticker, query)` used by the agent's tool-calling loop.
   - `EdgarClient`: Downloads SEC filings (10-K, 10-Q) using `sec-edgar-downloader`.
- **Persistence Layer**:
   - `DatabaseManager` upserts price bars (`INSERT ... ON CONFLICT DO UPDATE` on `timestamp` + `ticker`) so re-running the pipeline for overlapping date ranges updates existing rows instead of failing on duplicates.
   - News articles and SEC filings are checked against their natural unique keys (`article_id`, `accession_number`) before insert, so repeated ingestion runs are idempotent.
- **Intelligence Layer**:
   - `SentimentScorer`: Analyzes news sentiment to provide bullish/bearish tilts.
   - **LLM Integration**: Local integration with **Ollama** for multi-step reasoning and report synthesis. Currently configured for `gemma4:31b-cloud`.
- **Execution Entry Point**:
  `run_research.py` provides a runnable script to execute the full pipeline for a given ticker.

### Sample Output

Running `python run_research.py` produces a structured research brief. The agent may perform multiple "thought steps" (tool calls) before outputting the final report.

**Example Report for NVDA:**

```text
**EQUITY RESEARCH BRIEF: NVIDIA Corp (NVDA)**
**Date:** May 22, 2024
**Rating:** Neutral/Cautious (Short-term)

### #1. Executive Summary
NVDA is currently experiencing low-volatility price consolidation. While the technical price action remains slightly positive, it is countered by a bearish tilt in news sentiment. The high frequency of SEC filings suggests significant internal corporate activity or insider movements that warrant close monitoring.

### #2. Data Analysis
* **Price Action: Bullish Bias (Marginal)**
  * **Movement:** +0.82%
  * **Analysis:** The stock is exhibiting stability. A gain of less than 1% indicates a lack of conviction...

* **Sentiment Analysis: Bearish Tilt**
  * **Ratio:** 26 Positive / 31 Negative
  * **Analysis:** News sentiment is leaning negative...

* **Regulatory Filings: High Activity**
  * **Volume:** 10 recent SEC filings.
  * **Analysis:** A cluster of 10 filings in a short window typically indicates insider trading...

### #3. Risk vs. Opportunity Matrix
| **Opportunities (Upside)** | **Risks (Downside)** |
| :--- | :--- |
| **Price Support:** The stock is holding its ground... | **Sentiment Decay:** Negative news sentiment... |
| **Information Asymmetry:** High filing volume... | **Overvaluation:** Bearish sentiment... |

### #4. Final Outlook
**Short-Term Outlook: Neutral.**
The narrow price gain is insufficient to override the negative sentiment trend.
```

## Setup Instructions

### 1. Prerequisites

- **Python 3.11+**
- **PostgreSQL** with the **TimescaleDB** extension. The quickest path is Docker:
   ```bash
   docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=yourpassword -v timescale_data:/home/postgres/pgdata/data timescale/timescaledb-ha:pg17
   ```
- **Ollama** installed and running locally (or configured for a cloud-hosted model, as with `gemma4:31b-cloud`).

### 2. Model Setup

Pull or configure the model used by the research agent, matching whatever you set as `OLLAMA_MODEL` in your `.env`:

```bash
ollama pull gemma4:31b-cloud
```

### 3. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Fill in your API keys and connection details in `.env`:
   - `DATABASE_URL` (e.g. `postgresql://postgres:yourpassword@localhost:5432/finagent`)
   - `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`
   - `NEWS_API_KEY`
   - `SEC_USER_AGENT` (must be a valid email address for SEC EDGAR access)
   - `OLLAMA_MODEL`

### 4. Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

### 5. Database Setup

Create the database and enable the TimescaleDB extension:

```sql
CREATE DATABASE finagent;
\c finagent
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

Then initialize the schema and convert `prices` into a hypertable:

```bash
python -m db.models
```

## Project Structure

- `/agents`: Research agent implementation (`research_agent.py`).
- `/data_ingestion`: Client modules (`yfinance_client.py`, `news_client.py`, `edgar_client.py`, `alpaca_client.py`).
- `/ml`: Intelligence modules (`sentiment_scorer.py`, `quant_analyzer.py`).
- `/db`: Database schemas (`models.py`) and persistence logic (`manager.py`).
- `/config`: Configuration management.
- `/tests`: Test suite for all modules.

## Development Workflow

This project follows **Test-Driven Development (TDD)**. Run tests using:

```bash
pytest
```

## Development Log

### 2026-09-20

- **Refactored ResearchAgent to Agentic Loop**:
   - Transitioned `analyze()` from a linear pipeline to a multi-step reasoning loop (Plan → Execute → Observe).
   - Implemented tool-calling syntax (`ACTION: tool_name` / `ARGS: ...`) allowing the LLM to request specific news or SEC filing sections on-demand, or respond `FINAL:` when no further research is needed.
   - Integrated tool handlers for `fetch_specific_news`, `fetch_filing_section`, and `get_quant_metrics`, and removed duplicate method definitions left over from an earlier pass.
   - Added iteration capping (max 3) and fallback reporting to ensure termination even if a planning step fails.
   - Moved the ad-hoc NewsAPI request out of the agent and into a proper `NewsClient.search_news()` method, sharing request/parsing logic with `fetch_news()`.

### 2026-09-19

- **Improved Database Support**:
   - Enhanced `DatabaseManager` integration within the ResearchAgent to ensure stable persistence of ingested data.
   - Replaced unconditional inserts with upsert / existence-check logic for prices (`ON CONFLICT DO UPDATE`), news articles, and SEC filings, so repeated ingestion runs are idempotent instead of failing on duplicate keys.
   - Optimized the `Price` model schema and data insertion logic in `db/models.py` and `db/manager.py` for better alignment with TimescaleDB's hypertable requirements.
- **Stability Fixes**: Resolved import issues and refined session management in the database layer to improve the robustness of the research pipeline.
- **Verification**: Validated the end-to-end flow from data ingestion to LLM report generation using `run_research.py`.
