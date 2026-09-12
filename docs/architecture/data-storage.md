# Data and Storage Architecture

## Storage decisions

| Data class | System of record | Retention and access |
|---|---|---|
| Raw vendor responses and documents | S3-compatible object storage | Immutable, source/checksum/license metadata; long retention |
| Normalized market bars, actions, fundamentals | TimescaleDB or ClickHouse | Append/correct with provenance; query by symbol and event time |
| Product, portfolios, simulation orders, ledger | PostgreSQL | Transactional, row-level tenant isolation |
| Features and training snapshots | Parquet in object storage; DuckDB/Polars for development | Versioned point-in-time datasets |
| Research chunks and embeddings | PostgreSQL + pgvector | Citation and embedding-model version retained |
| Models, strategies, prompts, evaluations | MLflow plus Git/object storage | Immutable registry references; explicit promotion states |
| Logs, metrics, traces | Loki/Prometheus/Tempo-compatible stack | Short/medium retention; redacted |

## Data lineage and time semantics

Each source event has `source_event_time`, `observed_at`, `ingested_at`, `effective_at`, `source_id`, checksum, schema version, and license label. Feature and prediction reads must use an `as_of_time`. Historical simulation uses only facts known before that time. Corporate-action adjustments and revised fundamentals are recorded as new versions rather than silently overwriting history.

## Prediction ledger

The ledger is append-only. A correction links to a prior record; it never mutates the original decision. Minimum record fields:

```text
ledger_id, decision_time, as_of_time, account_scope, instrument, horizon,
candidate_action, confidence, expected_return, uncertainty, strategy_version,
model_versions, feature_set_version, dataset_snapshot_id, research_citation_ids,
prompt_version, agent_trace_id, risk_policy_version, risk_result,
backtest_or_paper_run_id, created_at, parent_ledger_id, outcome_status
```

Sensitive account identifiers are pseudonymized in analytics. Evidence text is retained only when licensed and authorized.
