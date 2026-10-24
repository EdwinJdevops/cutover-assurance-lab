# Adversarial product review — 24 October 2026

## Decision

HOLD commercialization. Continue a narrowly bounded validation effort, not a broad platform build. The repository is a useful synthetic failure laboratory. It is not yet evidence of a business, differentiated safety mechanism, or production cutover capability.

This review uses inspected code and the verified CI report, plus public primary-source documentation. No buyer interviews, competitor executions, market-size estimates, willingness-to-pay evidence, or production validation were performed. Product and buyer statements below are hypotheses unless explicitly marked as observed.

## What the evidence actually buys us

Observed: implementation 3e6c8c8 passed seven coordinator tests and produced 17 inspected synthetic scenario records in run 40093273989. The journal survives selected process deaths; missing, conflicting, stale and unapplied markers are rejected. This supports narrow implementation claims.

It does not establish incident reduction, operational adoption, correctness on arbitrary PostgreSQL schemas, acceptable assessment cost, or purchase intent. Seventeen scenario records are not seventeen independent customer deployments or a statistical safety rate. Six UNKNOWN outcomes and eleven NO-GO outcomes do not measure approval accuracy: GO is unavailable by construction.

The earlier review's statements that there was no journal, crash injection or transaction marker are now historical. Those components exist; the larger guarantees remain unproven.

## Four hostile readings

| Lens | Strongest objection | Evidence that would change the judgment |
|---|---|---|
| Investor | Why is this a company rather than a script, open-source contribution or migration consultancy deliverable? No recurring budget, distribution advantage or defensible asset is demonstrated. | Repeated costly workflow failure, named budget owners and paid demand for substantially the same deliverable across independent organizations. |
| Market researcher | Database migration anxiety is too broad. Cluster migration, schema evolution, replication monitoring and disaster recovery are different jobs. | Recent incident/runbook evidence identifying the same missing cutover evidence across a narrow segment. |
| Business developer | A team may need this once, distrust extra privileged software, and already pay its migration provider to own the outcome. | A specific upcoming rehearsal, accepted access boundaries, an actual procurement path and a buyer explaining why its current supplier cannot meet the need. |
| Competitor | We already compare rows and expose replication health. We can add an evidence export, while you have no installed base. | A reproducible failure our baseline misses, with independently reviewable evidence, lower operator burden and a purchasing consequence. |

No source reviewed proves that any named competitor lacks the proposed evidence workflow. Absence from a documentation page is not proof of absence from a product.

## Substitutes we must beat

| Substitute | Verified documented capability | Implication and boundary |
|---|---|---|
| PostgreSQL plus operator runbook | Native replication has explicit restrictions around schema/DDL, sequences and large objects. [Restrictions](https://www.postgresql.org/docs/16/logical-replication-restrictions.html) | Detecting documented limitations is useful but does not establish novelty. A disciplined DBA remains the control baseline. |
| pgcopydb | Compares schema and data, including row counts/checksums; cloning exposes follow and resume options. Schema comparison coverage is explicitly limited. [Compare](https://pgcopydb.readthedocs.io/en/latest/ref/pgcopydb_compare.html), [Clone](https://pgcopydb.readthedocs.io/en/latest/ref/pgcopydb_clone.html) | Closest initial PostgreSQL-to-PostgreSQL baseline. We have inspected docs, not benchmarked it. Do not claim it provides complete cutover assurance or that it cannot be extended. |
| AWS DMS | Supports row validation and validation-only workflows, with resource costs and documented limitations. [Validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html) | Comparison alone is occupied territory. Documentation research only; no AWS account or service was accessed. |
| AWS DMS resync | Automatically repairs selected validation failures, with documented engine and endpoint restrictions: Oracle/SQL Server sources, PostgreSQL-compatible targets. [Resync](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.DataResync.html) | Do not falsely claim this feature covers PostgreSQL-source resync. Its existence still weakens a generic reconciliation pitch. |
| Datafold | Vendor describes value-level comparison across datasets and migration use cases. This is vendor positioning, not our measured result. [Product](https://www.datafold.com/data-diff/) | Commercial comparison is crowded. The archived open-source data-diff repository is distinct from the current commercial offering. [Archive](https://github.com/datafold/data-diff) |
| pgroll | Documents reversible schema migrations and simultaneous schema versions. [Repository](https://github.com/xataio/pgroll) | Adjacent schema-evolution tool, not a like-for-like cross-cluster replacement. Do not inflate the competitive matrix by conflating the jobs. |

## Technical objections still capable of killing the proposition

1. The coordinator is detached from the database workflow. A FENCED journal transition does not execute or verify the PostgreSQL fence. Journal crash recovery is not recovery of a partially completed cutover. There is no integrated reconciliation contract for a crash between database action and journal persistence.
2. The negative decision policy is deliberately conservative. It establishes refusal, not a validated approval classifier. Evaluate whether each fault is correctly diagnosed and whether evidence can remain misleadingly complete; do not present zero GO as measured zero unsafe approvals.
3. The schema fingerprint is partial: column name, broad data type and nullability. It omits constraints, indexes, defaults, detailed type parameters and other objects. The existing added-column test does not establish general schema equivalence.
4. Full ledger fetch, Python materialization and JSON hashing scale with all rows. The fence holds a table lock while calculating the fingerprint. Five-second lock_timeout bounds acquisition, not time holding the lock or completing the scan. No production-sized latency/memory or writer-impact claim is supported.
5. The sequence check assumes a simple ascending increment-one sequence. It is not a general proof for altered increment, cycling, exhaustion or richer identity configurations.
6. Same-subscription markers are useful, but both databases are writable with lab superuser credentials. A marker and recomputable JSON hash are not independent trusted evidence. Expiry is not authentication.
7. Kill/restart covers process death with retained storage after convergence. It does not establish crash recovery during an in-flight replicated transaction, restore correctness, split-brain protection, or irreversible side-effect handling.
8. Equal fingerprints under separate snapshots do not establish application quiescence. Old writers, queues, routing, dependencies and external effects remain outside the model.

These are code-inspection findings and coverage gaps, not claims that every omitted case has been reproduced as a failure. Keep VERIFIED and PROMOTED disabled.

## Narrow commercial hypothesis worth testing

Hypothesis: PostgreSQL migration consultancies or platform teams with repeated cluster migrations lose meaningful engineering time assembling and reviewing cutover evidence across tools.

Proposed first deliverable: a reproducible rehearsal and evidence-review package that plugs into an existing migration runbook. Human owners retain cutover authority. Avoid introducing another migration engine or an AI decision-maker.

Consultancies are a candidate channel because repeated client work could improve frequency; this is unverified. A one-off engagement may justify a service, not a recurring software subscription. A fixed rehearsal fee is a pricing experiment, not a validated price.

The measurable job is: reduce time to assemble and independently review a specific cutover evidence packet without losing required findings or expanding dangerous privileges. Do not sell a general promise to prevent outages.

## Next validation sequence and stop rules

These thresholds are proposed management rules, not market statistics.

1. Interview five independently recruited owners who personally led a PostgreSQL cluster migration in the past year or have one planned. Include at least two service providers. Record role, last migration, trigger, current stack, runbook steps, evidence preparation time, failure/delay cost, signoff owner and budget owner. Redacted artifacts are stronger than compliments.
2. Ask about the last event before presenting the solution: What nearly blocked cutover? Which evidence changed the decision? What did your existing tools miss? Who assembled it, how long did it take, and why was the runbook insufficient? What access would a new tool be refused? What is the next funded migration?
3. Demand behavioral evidence: at least three of five describe the same concrete gap and offer a redacted artifact or detailed walkthrough; at least two agree to a bounded rehearsal; at least one budget owner accepts a paid scoped engagement or a documented procurement step. A free demo invitation or positive survey response does not count as willingness to pay.
4. Run a synthetic head-to-head baseline before major new implementation: native PostgreSQL checks plus a written runbook, pgcopydb where applicable, and this lab on identical seeded fixtures. Predeclare expected findings. Measure diagnosis correctness, missing evidence, review time, manual steps, runtime, memory and privilege requirements. Do not deploy AWS to compare DMS; treat it as a documentation comparison unless scope later changes.
5. Choose the first engineering slice from demonstrated evidence. If end-to-end recovery is the buyer's gap, integrate action intents, idempotency and reconciliation in the synthetic workflow before adding a UI. If evidence assembly is the gap, prove a reviewer can reproduce findings before adding automated decisions.

Stop or narrow if fewer than three interviewees independently substantiate the same gap; if existing tooling/runbooks address it with comparable effort; if nobody owns a budget; or if required access is consistently unacceptable. If buyers value bespoke engineering but not repeatable software, pursue a service deliberately rather than calling it SaaS.

A proposed performance gate for a rehearsal is at least 30% lower evidence-preparation/review time than the agreed baseline, with no missed predefined critical findings. This is a hypothesis to negotiate before measurement, not a result. Successful synthetic evaluation still cannot authorize production cutover.

## Positioning and credibility rules

Allowed: "Synthetic PostgreSQL cutover evidence and failure-recovery laboratory with reproducible CI scenarios."

Unproven: "Independent assurance platform", "production-ready coordinator", "zero-downtime guarantee", "prevents data loss", "compliance certified", "market validated" or a quantified incident-reduction claim.

Potential defensibility would need to be earned through customer-validated runbook integrations, trustworthy evidence provenance and a substantial reproducible failure corpus. None is a moat merely because it is planned. An LLM-generated explanation or dashboard does not resolve these gaps.

## Immediate result

Public evidence establishes substantial substitutes, not an empty market. Repository evidence establishes an improving laboratory, not product-market fit. The next commercial milestone is independently documented buyer behavior. The next technical milestone is a fair comparative experiment and an integrated recovery contract if that is what buyers need.

No outreach was sent, no interviews were invented, no competitor benchmark was represented as executed, and no AWS or production operation was performed. No new CI run is warranted for this documentation-only review.
