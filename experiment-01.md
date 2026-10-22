# Experiment 01: evidence-backed cutover decisions

Scope: synthetic ledger only, disposable PostgreSQL 16 source and target. No customer data, no production targets.

## Hypothesis
Existing PostgreSQL logical replication supplies row changes but does not by itself establish application cutover readiness. We test what independent evidence is needed before permitting a decision.

## Invariants
- Each synthetic transfer has exactly two ledger entries whose amounts sum to zero.
- Source and target ledger content must match when source writes are fenced.
- Target schema and identity sequence must be safe.
- Missing evidence is UNKNOWN, observed failure is NO-GO.
- GO is prohibited until independently verified replay watermark, external dependencies, application-wide write fencing and rollback semantics are implemented.

## Tests
Baseline after replication and explicit sequence synchronization: UNKNOWN.
Target schema divergence: NO-GO.
Target ledger corruption: NO-GO.
Target identity sequence rewind: NO-GO.

## Unimplemented experiments
Replication stall, coordinator crash, post-cutover writes, unsafe rollback. These must not be represented as tested.

## Business falsification
Compare with native PostgreSQL tooling, DMS validation and operational runbooks. Interview engineers who performed real migrations. Do not infer demand from the CBN deadline alone.
