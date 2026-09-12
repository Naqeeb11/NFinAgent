# FinAgent API Boundaries

## External API

The public API is versioned (`/v1`) and uses OAuth2/OIDC access tokens. It exposes only research, simulation, and audit capabilities.

| Boundary | Examples | Rules |
|---|---|---|
| Research | `GET /research/{instrument}`, `POST /research/runs` | Return source citations and freshness |
| Predictions | `GET /predictions`, `GET /predictions/{ledger_id}` | Ledger ID required for drilldown; no mutation |
| Backtests | `POST /backtests`, `GET /backtests/{run_id}` | Dataset/strategy versions required |
| Paper trading | `POST /paper-runs`, `GET /paper-runs/{id}/positions` | Simulated orders only; explicit assumption set |
| Copy-trading simulation | `POST /shadow-accounts/{id}/follow` | Mirrors simulated activity; no custody or order routing |
| Evaluation | `GET /evaluations`, `GET /drift` | Present metrics and promotion decisions |
| Administration | registry/policy CRUD | Least privilege, approval/audit trail |

## Internal contracts

Use OpenAPI for request/response APIs and AsyncAPI/JSON Schema for events. Services may read their own stores only. Cross-domain reads go through contract APIs, materialized projections, or events. Ledger writes are permitted only through the ledger service.

## Forbidden boundaries

- No endpoint that submits an order to a broker or exchange.
- No agent tool that writes directly to portfolios, risk limits, registries, or data stores.
- No client-supplied model, strategy, or prompt version without allow-list validation.
