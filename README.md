# Cutover Assurance Lab

Research-only PostgreSQL cutover and failure-injection laboratory. The goal is to evaluate whether existing database migration tooling leaves a reproducible gap in evidence-backed cutover decisions.

**Status: unverified experiment.** No database tests have been run in GitHub Actions yet. The experiment must never be connected to production systems or real payment data. It does not claim regulatory compliance or safe cutover authorization.

## Experiment 01

- Synthetic ledger transactions, disposable PostgreSQL source and target
- Native PostgreSQL logical replication
- Assessment outcomes: `UNKNOWN` or `NO-GO`; `GO` is intentionally unavailable
- Planned fault cases: schema divergence, destination corruption, unsafe sequence state
- Remaining work: replication stall, coordinator crash, unsafe rollback boundary, verified write fencing and independently validated evidence

## Running the lab

GitHub Actions is the intended test environment; no AWS account or local Docker is required. The CI workflow is activated once the `lab/` source files are committed. See `experiment-01.md` for the investigation protocol.

Do not infer successful execution from a committed workflow: inspect Actions logs and evidence artifacts.
