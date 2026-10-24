"""Execute disposable integration scenarios on a GitHub-hosted Docker runner."""
import json, pathlib, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"evidence"
OUT.mkdir(exist_ok=True)

def run(*args,check=True):
    p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f"{args!r} exit {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p

def assess():
    p=run(sys.executable,"lab.py","assess")
    return json.loads(p.stdout)

def wait_for(expected,reason):
    last=None
    for _ in range(30):
        last=assess()
        if last["decision"]==expected and any(reason in r for r in last["reasons"]):
            return last
        time.sleep(2)
    raise AssertionError(f"Expected {expected}: {reason}; last={last}")

def fresh():
    run("docker","compose","down","-v","--remove-orphans")
    run("docker","compose","up","-d","--wait")
    run(sys.executable,"lab.py","setup")
    run(sys.executable,"lab.py","seed","20")
    run(sys.executable,"lab.py","fence")
    for _ in range(60):
        data=assess()
        a,b=data.get("source",{}),data.get("target",{})
        if a.get("rows")==40 and b.get("rows")==40 and a.get("digest")==b.get("digest"):
            break
        time.sleep(2)
    else:
        raise AssertionError("Initial logical replication did not converge")
    # PostgreSQL does not replicate sequence state. Establish a safe baseline explicitly.
    run(sys.executable,"lab.py","sync-sequence")

def stall_replication():
    # Stop subscriber apply without destroying the replication slot.
    with __import__("psycopg").connect("postgresql://postgres:labonly@localhost:55433/ledger",autocommit=True) as target:
        target.execute("ALTER SUBSCRIPTION ledger_sub DISABLE")
    # Source writes after the subscriber stops must not be mistaken for replicated state.
    with __import__("psycopg").connect("postgresql://postgres:labonly@localhost:55432/ledger",autocommit=True) as source:
        event=__import__("uuid").uuid4()
        source.execute("INSERT INTO ledger_entries(event_id,account_id,amount) VALUES (%s,%s,%s),(%s,%s,%s)", (event,"payer",-100,event,"payee",100))

def record(name,data):
    (OUT/f"{name}.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")

def barrier_scenarios():
    import psycopg
    from lab import SOURCE, TARGET
    fresh()
    record("barrier-applied",wait_for("UNKNOWN","missing independently verified"))
    # Equal ledger contents alone must never mask a marker that did not apply.
    with psycopg.connect(TARGET,autocommit=True) as dst:
        dst.execute("ALTER SUBSCRIPTION ledger_sub DISABLE")
    run(sys.executable,"lab.py","fence")
    record("barrier-not-applied",wait_for("NO-GO","transaction-linked barrier mismatch"))
    with psycopg.connect(TARGET,autocommit=True) as dst:
        dst.execute("ALTER SUBSCRIPTION ledger_sub ENABLE")
    record("barrier-resumed",wait_for("UNKNOWN","missing independently verified"))
    # An uncommitted marker is invisible, and rollback must preserve the old marker.
    with psycopg.connect(SOURCE,autocommit=True) as src:
        before=src.execute("SELECT token FROM cutover_barrier").fetchone()
        src.execute("BEGIN")
        src.execute("UPDATE cutover_barrier SET token=gen_random_uuid()")
        with psycopg.connect(SOURCE,autocommit=True) as observer:
            assert observer.execute("SELECT token FROM cutover_barrier").fetchone()==before
        src.execute("ROLLBACK")
        assert src.execute("SELECT token FROM cutover_barrier").fetchone()==before
    record("barrier-rollback",wait_for("UNKNOWN","missing independently verified"))
    # Force actual PostgreSQL process death, retaining container data directories.
    run("docker","compose","kill","-s","SIGKILL","source","target")
    unavailable=assess()
    assert unavailable["decision"] != "GO"
    assert any("evidence unavailable" in r for r in unavailable["reasons"])
    record("postgres-unavailable",unavailable)
    run("docker","compose","up","-d","--wait")
    record("postgres-crash-restart",wait_for("UNKNOWN","missing independently verified"))
    for kind,sql,reason in [
        ("missing","DELETE FROM cutover_barrier","missing"),
        ("conflict","UPDATE cutover_barrier SET source_txid='wrong'","mismatch")]:
        with psycopg.connect(TARGET,autocommit=True) as dst:
            dst.execute(sql)
        record("barrier-"+kind,wait_for("NO-GO","transaction-linked barrier "+reason))
        fresh()
        wait_for("UNKNOWN","missing independently verified")
    with psycopg.connect(SOURCE,autocommit=True) as src:
        src.execute("UPDATE cutover_barrier SET created_at=clock_timestamp()-interval '10 minutes'")
    record("barrier-expired",wait_for("NO-GO","expired or future dated"))
    run(sys.executable,"lab.py","fence")
    wait_for("UNKNOWN","missing independently verified")
    # Both ledgers can agree yet disagree with their older barrier.
    with psycopg.connect(SOURCE,autocommit=True) as src:
        src.execute("UPDATE lab_control SET writes_fenced=FALSE")
    run(sys.executable,"lab.py","seed","1")
    with psycopg.connect(SOURCE,autocommit=True) as src:
        src.execute("UPDATE lab_control SET writes_fenced=TRUE")
    run(sys.executable,"lab.py","sync-sequence")
    record("barrier-ledger-diverged",wait_for("NO-GO","barrier ledger mismatch"))


def main():
    try:
        barrier_scenarios()
        fresh()
        record("baseline",wait_for("UNKNOWN","missing independently verified"))
        # Deliberately remove the source write fence; assessment must fail closed.
        with __import__("psycopg").connect("postgresql://postgres:labonly@localhost:55432/ledger",autocommit=True) as source:
            source.execute("UPDATE lab_control SET writes_fenced=FALSE WHERE singleton")
        record("unfenced",wait_for("NO-GO","source write fence not enabled"))
        fresh()
        # Baseline source is fenced: explicitly release it to simulate new writes.
        with __import__("psycopg").connect("postgresql://postgres:labonly@localhost:55432/ledger",autocommit=True) as source:
            source.execute("UPDATE lab_control SET writes_fenced=FALSE WHERE singleton")
        stall_replication()
        record("replication-stall",wait_for("NO-GO","source/target row mismatch"))
        record("subscription-disabled",wait_for("NO-GO","logical subscription disabled or missing"))
        for kind,reason in [("schema","schema mismatch"),("corruption","source/target row mismatch"),("sequence","unsafe identity sequence")]:
            fresh()
            run(sys.executable,"lab.py","inject",kind)
            record(kind,wait_for("NO-GO",reason))
        print("PASS: transaction barrier, PostgreSQL crash/restart, baseline UNKNOWN and failure scenarios NO-GO")
    finally:
        run("docker","compose","down","-v","--remove-orphans",check=False)

if __name__=="__main__":main()
