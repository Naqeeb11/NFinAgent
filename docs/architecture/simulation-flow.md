# Backtesting Paper Trading and Copy Trading Simulation

```mermaid
sequenceDiagram
  participant D as Versioned data snapshot
  participant S as Strategy
  participant R as Risk policy
  participant L as Prediction ledger
  participant X as Simulator
  participant E as Evaluator
  D->>S: point-in-time features as_of T
  S->>R: candidate action and rationale
  R->>L: decision plus accept/reject and policy version
  L->>X: approved simulated instruction
  X->>X: model fills, costs, slippage, corporate actions
  X->>L: outcome references
  X->>E: returns, exposure, fill and portfolio facts
  E->>E: benchmark and regime evaluation
```

Backtests take an immutable dataset snapshot, code/strategy version, parameter set, calendar, starting capital, universe, fee model, slippage model, delay assumptions, and corporate-action policy. Results are invalid if any are missing.

Paper trading uses current market data and the same strategy/risk/ledger path. Copy trading means a shadow account follows another *simulated* account subject to its own risk limits; it does not copy brokerage accounts or transmit orders.
