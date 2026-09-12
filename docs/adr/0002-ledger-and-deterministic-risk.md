# ADR 0002 Immutable Ledger and Deterministic Risk

## Status

Accepted

## Decision

All candidate actions receive a deterministic risk decision and are persisted to an append-only prediction ledger before a simulator can act. LLM agents cannot bypass either component.

## Consequences

Every result is explainable and replayable. The design adds data discipline but prevents untraceable agent behavior.
