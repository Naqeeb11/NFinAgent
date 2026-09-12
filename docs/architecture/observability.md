# Observability and Auditability

Every request and scheduled run carries a correlation ID. OpenTelemetry traces connect ingestion, feature materialization, agent calls, model scoring, risk decisions, ledger writes, simulation fills, and evaluation jobs.

## Minimum signals

| Area | Metrics and evidence |
|---|---|
| Data | freshness, missing symbols, duplicate rate, late events, quality-rule failures |
| Agents | latency, token/cost budget, tool errors, schema validity, citation coverage, prompt injection flags |
| Models | scoring latency, confidence distribution, feature drift, calibration, regime performance |
| Simulation | rejected decisions, fills, slippage, drawdown, exposure, divergence from expected cost |
| Platform | API error rate, queue lag, consumer retries, database saturation, backup health |
| Audit | actor, action, request ID, policy/model/strategy versions, before/after registry states |

Dashboards use Grafana; logs use structured JSON with redaction; traces use OpenTelemetry. Alerting is actionable: stale critical market data, ledger write failure, policy bypass attempt, evaluation gate regression, or repeated model/agent errors.
