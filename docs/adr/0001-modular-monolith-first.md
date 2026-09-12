# ADR 0001 Modular Monolith First

## Status

Accepted

## Context

FinAgent needs clear future service boundaries but begins as a learning project with one primary developer and no production load.

## Decision

Build one deployable application with independently testable modules, explicit domain interfaces, an outbox, and versioned contracts. Extract a service only after replay, scale, reliability, or ownership needs are demonstrated.

## Consequences

Faster local development and less operational burden. Module boundaries must be enforced early to avoid a later distributed monolith.
