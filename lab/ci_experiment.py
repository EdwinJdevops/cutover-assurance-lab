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

def record(name,data):
    (OUT/f"{name}.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")

def main():
    try:
        fresh()
        record("baseline",wait_for("UNKNOWN","missing independently verified"))
        # Deliberately remove the source write fence; assessment must fail closed.
        with __import__("psycopg").connect("postgresql://postgres:labonly@localhost:55432/ledger",autocommit=True) as source:
            source.execute("UPDATE lab_control SET writes_fenced=FALSE WHERE singleton")
        record("unfenced",wait_for("NO-GO","source write fence not enabled"))
        for kind,reason in [("schema","schema mismatch"),("corruption","source/target row mismatch"),("sequence","unsafe identity sequence")]:
            fresh()
            run(sys.executable,"lab.py","inject",kind)
            record(kind,wait_for("NO-GO",reason))
        print("PASS: baseline UNKNOWN; unfenced/schema/corruption/sequence NO-GO")
    finally:
        run("docker","compose","down","-v","--remove-orphans",check=False)

if __name__=="__main__":main()
