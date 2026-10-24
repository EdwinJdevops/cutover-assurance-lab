# Cutover Assurance Lab

Research-only PostgreSQL cutover and failure-injection laboratory. The goal is to evaluate whether existing database migration tooling leaves a reproducible gap in evidence-backed cutover decisions.

**Status: research experiment; never cutover authorization.** Disposable PostgreSQL CI has passed on earlier commits; inspect the latest run for current verification. The experiment must never be connected to production systems or real payment data. It does not claim regulatory compliance or safe cutover authorization.

## Experiment 01

- Synthetic ledger transactions, disposable PostgreSQL source and target
- Native PostgreSQL logical replication
- Assessment outcomes: `UNKNOWN` or `NO-GO`; `GO` is intentionally unavailable
- Fault cases: schema divergence, destination corruption, unsafe sequence state, missing/conflicting/expired/unapplied barriers
- Recovery tests: forced coordinator death around journal commit and PostgreSQL process death with restart
- Remaining work: unsafe rollback boundary, application-wide fencing, independent authenticated evidence, distributed coordination

## Running the lab

GitHub Actions is the intended test environment; no AWS account or local Docker is required. The CI workflow is activated once the `lab/` source files are committed. See `experiment-01.md` for the investigation protocol.

Do not infer successful execution from a committed workflow: inspect Actions logs and evidence artifacts.

## Transaction-linked barrier and recovery contract

The fence operation drains existing ledger DML using a bounded table lock, then commits
the control flag and a fresh UUID marker in one source transaction. The marker carries
the source transaction ID, full ledger fingerprint and schema fingerprint. The ledger
and marker share one publication/subscription. The assessor requires matching committed
markers on both databases, matching fingerprints, age within five minutes, two ready
tables, an enabled subscription and a live apply worker. Received LSNs are diagnostic
only; they do not authorize a transition. PostgreSQL's single-subscription commit order
is the basis of the lab marker test:
https://www.postgresql.org/docs/16/logical-replication-architecture.html

Each database is read using a repeatable-read snapshot. There is no atomic cross-database
snapshot or ongoing protection after assessment. A marker is transaction-linked evidence,
not an independently authenticated commit-LSN watermark. Direct target writes, superuser
bypass, TRUNCATE, disabled triggers, old repeatable-read writers and external producers
are outside this lab fence's guarantee. Credentials and DSNs are fixed to disposable
localhost containers; environment DSN overrides are intentionally unsupported.

Coordinator tests terminate a child process after the state update, after the event
insert, and after COMMIT but before acknowledgement. Recovery checks SQLite integrity,
state/event atomicity, stale-revision refusal and retry behavior. Competing processes
must produce exactly one winning revision. This tests process death on local SQLite,
not power loss, filesystem loss, distributed consensus, leases or external side effects.
FENCED is a journal label, not proof that any external fence was enacted.
VERIFIED and PROMOTED remain refused even with matching lab barrier evidence.

Integration tests kill both PostgreSQL containers with SIGKILL, assess unavailability,
restart the same containers/data directories and require marker/data convergence.
This covers database process crash recovery, not host failure, restored backups,
replication-slot failover, network partitions, exactly-once external actions or scale.

## CI audit, 24 October 2026

The initial 17-run history contained five failures, three cancellations and nine
successes. Historical failures included missing lab files/cache inputs, command-line
usage errors and Python syntax errors. These were superseded by successful later runs,
including run 40000061740 at ce1aa05. Cancelled run 40000047831 had no jobs.
The current validation batch reruns the affected setup, syntax, coordinator and
PostgreSQL scenario steps on the updated revision; obsolete failing commits are not
rerun, to avoid spending Actions minutes on already corrected source.
See Actions logs and uploaded JSON artifacts for actual results; a commit alone is
not verification. AWS and production are outside this repository's execution scope.
