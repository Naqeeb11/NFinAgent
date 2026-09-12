# FinAgent Service Catalogue

| Component | Responsibility | First technology choice | Owns |
|---|---|---|---|
| API gateway and BFF | UI-facing API, auth propagation, rate limits | FastAPI | API contracts |
| Market data ingestion | Fetch, validate, deduplicate, timestamp source data | Python, Prefect, provider SDKs | Raw source manifests |
| Research ingestion | Collect filings, news, macro, and metadata under licensing rules | Python, Prefect | Research documents |
| Data quality | Freshness, completeness, anomaly and corporate-action checks | Great Expectations or custom rules | Quality findings |
| Feature pipeline | Time-aligned technical, fundamental, macro and sentiment features | Python, Polars, DuckDB | Feature definitions/materializations |
| Research corpus | Chunk, embed, retrieve source-backed research | pgvector initially | Corpus index and citations |
| Agent orchestrator | Coordinate research, critique and explanation workflows | LangGraph, provider LLM SDK | Agent traces and prompt refs |
| Quant prediction | Train, score and ensemble numeric models | scikit-learn, LightGBM, MLflow | Model outputs and versions |
| Strategy engine | Produce candidate trade intents from signals | Python domain library | Strategy version/output |
| Risk policy engine | Deterministic portfolio and simulation constraints | Python rules engine | Risk decisions/policy refs |
| Prediction ledger | Immutable decision provenance and outcome links | PostgreSQL | Ledger entries |
| Backtest engine | Event/time-aware historical simulation | Python, vectorbt-like custom core | Backtest runs |
| Paper-trading simulator | Simulated fills, portfolio and copy-trade shadow accounts | Python, PostgreSQL | Orders/fills/positions |
| Evaluation and learning | Score calibration, attribution, drift, candidate promotion | Python, Evidently, MLflow | Evaluations/promotions |
| Notification service | User alerts and reports, never trade execution | FastAPI worker | Delivery records |
| Observability | Logs, traces, metrics, lineage/audit dashboards | OpenTelemetry, Prometheus, Grafana | Telemetry |

See the workbook for owners, dependencies, deployment timing, data classes, and implementation status.
