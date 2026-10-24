# Verified synthetic lab results — 24 October 2026

Implementation commit: 3e6c8c8f1f096f0baf8f2caf518a8da563f47431.
CI: https://github.com/EdwinJdevops/cutover-assurance-lab/actions/runs/40093273989
Result: success; experiment job took 66 seconds. Setup, syntax, seven coordinator tests, PostgreSQL scenarios, artifact upload and cleanup all passed.

Downloaded and inspected all 17 JSON artifacts. Six were UNKNOWN and eleven NO-GO. No GO outcome exists.

| Scenario | Decision | Barrier matched |
|---|---|---|
| barrier-applied | UNKNOWN | True |
| barrier-conflict | NO-GO | False |
| barrier-expired | NO-GO | False |
| barrier-ledger-diverged | NO-GO | False |
| barrier-missing | NO-GO | False |
| barrier-not-applied | NO-GO | False |
| barrier-resumed | UNKNOWN | True |
| barrier-rollback | UNKNOWN | True |
| baseline | UNKNOWN | True |
| corruption | NO-GO | False |
| postgres-crash-restart | UNKNOWN | True |
| postgres-unavailable | UNKNOWN | unavailable |
| replication-stall | NO-GO | False |
| schema | NO-GO | False |
| sequence | NO-GO | True |
| subscription-disabled | NO-GO | False |
| unfenced | NO-GO | True |

Forced coordinator termination was tested after state update, after event insertion, and after COMMIT before acknowledgement. SQLite integrity, atomic journal recovery, stale retries and single-winner process contention passed locally on Windows and in Linux CI.

PostgreSQL source and target were killed with SIGKILL and restarted using the same container data directories. The unavailable assessment was UNKNOWN with an OperationalError; after restart, matching marker/data evidence returned UNKNOWN. Unapplied markers were tested with equal source/target ledger data and disabled subscriber apply.

Each record hash was recomputed after download and matched. This only checks record consistency; it is not an authenticated attestation.

## Verified limits

- Matching barriers never authorize VERIFIED or PROMOTED; both remain blocked.
- The marker carries source transaction identity and ledger state, not an independently authenticated commit-LSN watermark.
- Trigger fencing is limited to this synthetic ledger; application producers, superuser bypass, old snapshots, external side effects and TRUNCATE remain outside its guarantee.
- Repeatable-read is per database; no atomic cross-database snapshot or continuous fence guarantee.
- SQLite tests cover local process death, not power loss, multi-host consensus or lost storage.
- PostgreSQL restart tests cover container process death, not backup restoration, host loss or slot failover.
- Fixed localhost lab DSNs only. No AWS or production was accessed.
- CI emitted an action-runtime deprecation warning for the existing action versions; it did not fail a step.

## Historical CI treatment

Inspected the original 17 runs: nine successes, five failures, three cancellations. All three cancelled runs had zero jobs. Earlier failure logs showed missing lab/cache inputs, early execution failures (exit code 2), and a Python syntax error. Later runs already superseded these errors. The new validation run repeats dependency setup, syntax, coordinator and database steps on the corrected implementation rather than rerunning obsolete broken revisions.

Artifact retention in GitHub is three days. A local evidence ZIP accompanies this report.
