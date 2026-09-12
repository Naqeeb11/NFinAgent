# ADR 0004 Point in Time Data and Reproducibility

## Status

Accepted

## Decision

Feature retrieval and backtesting require `as_of_time` semantics, versioned source snapshots, and recorded adjustment policies.

## Consequences

Backtest integrity is stronger and data management is more demanding. Results can be independently reproduced.
