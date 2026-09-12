# FinAgent Event Topics

Kafka is a later-phase transport; in the modular-monolith phase the same contracts are emitted to an in-process outbox. All messages include `event_id`, `event_type`, `schema_version`, `occurred_at`, `producer`, `correlation_id`, and `causation_id`.

| Topic | Producer | Consumers | Key | Purpose |
|---|---|---|---|---|
| `market.raw.v1` | Market ingestion | Normalization | provider:symbol | Vendor payload reference and metadata |
| `market.normalized.v1` | Normalization | Features, quality | instrument:bar_time | Validated price/action facts |
| `research.document.v1` | Research ingestion | Corpus, agents | document_id | Source-backed research document |
| `feature.materialized.v1` | Feature pipeline | Prediction, backtest | instrument:as_of_time | Point-in-time feature set |
| `signal.candidate.v1` | Strategy engine | Risk engine | candidate_id | Candidate intent, not an order |
| `decision.risk-reviewed.v1` | Risk engine | Ledger, simulator | decision_id | Approved/rejected simulated decision |
| `ledger.recorded.v1` | Ledger | Simulator, evaluation | ledger_id | Immutable provenance reference |
| `simulation.fill.v1` | Backtest/paper simulator | Portfolio, evaluation | run_id:fill_id | Simulated fill/cost facts |
| `evaluation.completed.v1` | Evaluation | Registry, UI | evaluation_id | Metric, drift and gate result |
| `model.promotion.v1` | Registry | Prediction | model_name | Approved model/strategy pointer |

Topics are append-only, schema-validated, idempotent by `event_id`, and replayed into isolated consumers. PII and raw secrets are forbidden in event payloads; store references instead.
