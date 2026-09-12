# FinAgent Implementation Roadmap

## Delivery assumptions

This is a 36-week (about 8-9 month) plan for one backend engineer learning AI engineering while building in public. It assumes 15-25 focused hours per week. The order favors a small vertical slice, reproducibility, and safe simulation before richer agents or model complexity.

| Phase | Weeks | Outcome | Exit criteria |
|---|---:|---|---|
| 0 Design and foundations | 1-2 | Repo, contracts, local dev, sample dataset, baseline slice | Reproducible local run and architecture review |
| 1 Data foundation | 3-6 | Ingestion, normalization, quality, timeseries/object stores | Daily dataset is versioned, validated, replayable |
| 2 Research and features | 7-10 | Feature definitions, corpus, retrieval, cited research brief | Point-in-time features and cited briefs pass tests |
| 3 Prediction and strategies | 11-15 | Baselines, ensembles, registry, strategy contracts | Walk-forward benchmark and model cards created |
| 4 Ledger risk and backtesting | 16-20 | Append-only ledger, deterministic policy, event-driven backtest | Every backtest decision replays from ledger evidence |
| 5 Paper simulation and copy shadowing | 21-25 | Paper portfolios, fills, costs, shadow/copy simulation | No live order path; simulation audit trail complete |
| 6 Agents and evaluation | 26-30 | Orchestrated analysts, critic, drift and promotion gates | Agent trace/eval suite and human promotion flow working |
| 7 Reliability and public beta | 31-36 | Observability, security hardening, docs, demo deployment | Load/recovery tests, threat review, public release checklist |

## First two weeks

### Week 1: executable foundations

1. Create Python workspace, formatter/linter/type checker, test runner, and pre-commit hooks.
2. Turn the architecture contracts into JSON Schema and a minimal OpenAPI document.
3. Add Docker Compose for PostgreSQL, object storage emulator, and a local application process.
4. Choose one liquid market/universe and one licensed/free daily-data source. Record its terms and data contract.
5. Implement only a local fixture-data loader and normalized daily-bar schema.
6. Create a basic lineage record: source manifest, checksum, observed time, and schema version.
7. Add unit tests for schema validation and duplicate/out-of-order handling.

### Week 2: first vertical slice

1. Add a simple moving-average or momentum baseline strategy with versioned parameters.
2. Materialize point-in-time features from fixture data.
3. Implement a minimal ledger write path and deterministic risk rules: data freshness, max position, max portfolio exposure, and reject-on-missing metadata.
4. Implement a daily-bar backtest with declared fees, slippage, universe, capital, and look-ahead tests.
5. Produce one evaluated run: return, drawdown, turnover, benchmark comparison, and a ledger drilldown.
6. Publish a concise architecture and first-run report. Do not introduce agents, vector search, or live data until this slice is reproducible.

## Monthly public milestones

| Month | Public artifact |
|---:|---|
| 1 | Design freeze, local baseline, data-contract post |
| 2 | Data-quality and lineage demo |
| 3 | Feature and research-citation demo |
| 4 | Model benchmark and model card |
| 5 | Ledger/replay and backtesting demo |
| 6 | Paper portfolio and copy-shadow demo |
| 7 | Agent evaluation and safety report |
| 8-9 | Reliability hardening, security review, v0.1 release |

## Suggested backlog order

Keep one vertical slice working at all times. Prioritize: correctness tests, data lineage, time-split evaluation, ledger/replay, risk controls, paper simulation, observability, then agent sophistication. Treat production microservice extraction, Kafka, Kubernetes, multi-asset support, and live execution as later decisions rather than early milestones.
