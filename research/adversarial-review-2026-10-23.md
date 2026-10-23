# Adversarial review — 23 October 2026

## Investment verdict: HOLD
Research prototype only. No validated buyer, no defensible novelty claim, no production GO authorization.

## Competitor's strongest rebuttal
AWS DMS already validates full loads and CDC changes and exposes mismatch and validation-only workflows. PostgreSQL itself exposes subscription worker state, table synchronization status and replication slot metrics. Replicating these capabilities is not a product moat.

References:
- https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html
- https://www.postgresql.org/docs/16/logical-replication-monitoring.html

## Technical weaknesses in current experiment
1. **Evidence inconsistency:** source and target fingerprints are read in separate snapshots; they are not an atomic cross-database snapshot. An unfenced writer can race the assessor.
2. **Insufficient fence:** a database trigger and control flag are not proof that all application writers, queues, schedulers and external producers are quiescent.
3. **No replay watermark proof:** received_lsn/latest_end_lsn are not equivalent to independent evidence that every relevant transaction was applied. Table readiness and live apply worker are necessary, not sufficient.
4. **Untrusted decision artifact:** a SHA-256 over JSON is not an authenticated attestation. Anyone who can alter the record can recompute its hash.
5. **No recovery protocol:** no durable coordinator state, crash injection, idempotent retry, split-brain protection or rollback boundary.
6. **Toy ledger:** 20 synthetic transfers do not model hot tables, multi-table transaction ordering, DDL, external side effects, backpressure or scale.
7. **Commercial evidence absent:** no buyer interviews, migration frequency, cost of incidents, willingness to pay or deployment friction measurements.

## Non-negotiable gates before a GO state can exist
- Durable, monotonically advancing coordinator state with recovery contracts and single-writer lease/fencing.
- Source cutover barrier and independently confirmed subscriber apply progress beyond the barrier.
- Stable source/target comparison under a documented consistency model.
- Application-level producer fencing and independent dependency checks.
- Explicit irreversible side-effect boundary and operator-authorized rollback policy.
- Authenticated, versioned evidence with provenance and expiration.
- Failure injection proving that missing, stale, conflicting and corrupted evidence cannot produce GO.

## Product falsification criteria
- If existing DMS/PostgreSQL/runbook controls cover the target incident with comparable operational cost, do not build a competing product.
- If five qualified migration owners cannot identify a costly gap or credible purchase path, pause commercialization.
- If a safe cutover requires invasive integrations that exceed the migration team's tolerance, narrow the scope or stop.

## Immediate scope
Improve the assessor's rejection of absent apply workers and incomplete table sync. Next: implement a transaction-linked cutover barrier and coordinator crash tests. Do not claim those are complete before CI evidence exists.
