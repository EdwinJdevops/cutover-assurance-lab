"""Disposable PostgreSQL logical replication experiment. Synthetic data only."""
import argparse, hashlib, json, os, sys, uuid
from datetime import datetime, timezone
import psycopg

SOURCE = os.getenv("SOURCE_DSN", "postgresql://postgres:labonly@localhost:55432/ledger")
TARGET = os.getenv("TARGET_DSN", "postgresql://postgres:labonly@localhost:55433/ledger")

def connect(dsn):
    return psycopg.connect(dsn, connect_timeout=5, autocommit=True)

def setup():
    with connect(SOURCE) as src, connect(TARGET) as dst:
        src.execute("CREATE PUBLICATION ledger_pub FOR TABLE ledger_entries")
        dst.execute("CREATE SUBSCRIPTION ledger_sub CONNECTION 'host=source port=5432 dbname=ledger user=postgres password=labonly' PUBLICATION ledger_pub WITH (copy_data=true)")
    print("Logical replication configured")

def seed(n):
    with connect(SOURCE) as src:
        with src.transaction():
            for _ in range(n):
                event = uuid.uuid4()
                src.execute("INSERT INTO ledger_entries(event_id,account_id,amount) VALUES (%s,%s,%s),(%s,%s,%s)", (event,"payer",-100,event,"payee",100))
    print(f"Seeded {n} balanced synthetic transfers")

def fence():
    with connect(SOURCE) as src:
        src.execute("UPDATE lab_control SET writes_fenced=TRUE WHERE singleton")
    print("Lab-level source trigger enabled; not application-wide fencing")

def sync_sequence():
    # Logical replication does not advance subscriber identity sequences.
    # Explicitly repair this known gap; the action is logged in CI.
    with connect(TARGET) as dst:
        with dst.transaction():
            with dst.cursor() as c:
                c.execute("SELECT coalesce(max(id),0) FROM ledger_entries")
                max_id = c.fetchone()[0]
                c.execute("SELECT setval(pg_get_serial_sequence('ledger_entries','id'), %s, %s)", (max(1,max_id), max_id > 0))
    print(f"Explicitly synchronized target identity sequence at row id {max_id}")

def fingerprint(conn):
    with conn.cursor() as c:
        c.execute("SELECT event_id::text,account_id,amount FROM ledger_entries ORDER BY event_id,account_id")
        rows = c.fetchall()
        digest = hashlib.sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest()
        c.execute("SELECT event_id::text,count(*),sum(amount) FROM ledger_entries GROUP BY event_id HAVING count(*)<>2 OR sum(amount)<>0")
        broken = c.fetchall()
        c.execute("SELECT max(id),count(*) FROM ledger_entries")
        max_id,count = c.fetchone()
        c.execute("SELECT pg_get_serial_sequence('ledger_entries','id')")
        sequence_name = c.fetchone()[0]
        c.execute("SELECT last_value,is_called FROM " + sequence_name)
        last_value,is_called = c.fetchone()
        safe = max_id is None or (last_value + (1 if is_called else 0) > max_id)
        c.execute("SELECT md5(string_agg(column_name||':'||data_type||':'||is_nullable,',' ORDER BY ordinal_position)) FROM information_schema.columns WHERE table_schema='public' AND table_name='ledger_entries'")
        schema_hash = c.fetchone()[0]
    return {"rows":count,"digest":digest,"broken_events":broken,"sequence_safe":safe,"schema_hash":schema_hash}

def assess():
    result={"time_utc":datetime.now(timezone.utc).isoformat(),"decision":"UNKNOWN","reasons":[],"scope":"Synthetic ledger; never production approval"}
    try:
        with connect(SOURCE) as src, connect(TARGET) as dst:
            a,b=fingerprint(src),fingerprint(dst)
            result["source"],result["target"]=a,b
            with src.cursor() as c:
                c.execute("SELECT writes_fenced FROM lab_control WHERE singleton")
                fenced=c.fetchone()[0]
                c.execute("SELECT pg_current_wal_lsn()::text")
                result["source_current_lsn"]=c.fetchone()[0]
            with dst.cursor() as c:
                c.execute("SELECT received_lsn::text,latest_end_lsn::text FROM pg_stat_subscription WHERE subname='ledger_sub'")
                subscription=c.fetchone()
            result["target_subscription"]=subscription
            with dst.cursor() as c:
                c.execute("SELECT subenabled FROM pg_subscription WHERE subname='ledger_sub'")
                row=c.fetchone()
                result["subscription_enabled"]=bool(row[0]) if row else False
            if a["schema_hash"]!=b["schema_hash"]: result["reasons"].append("schema mismatch")
            if a["digest"]!=b["digest"]: result["reasons"].append("source/target row mismatch")
            if a["broken_events"] or b["broken_events"]: result["reasons"].append("unbalanced or incomplete synthetic event")
            if not a["sequence_safe"] or not b["sequence_safe"]: result["reasons"].append("unsafe identity sequence")
            if not fenced: result["reasons"].append("source write fence not enabled")
            if not result["subscription_enabled"]: result["reasons"].append("logical subscription disabled or missing")
            if not subscription or not subscription[0]: result["reasons"].append("subscription not reporting received LSN")
            if result["reasons"]: result["decision"]="NO-GO"
            else: result["reasons"].append("missing independently verified replay watermark, dependency health, and rollback evidence")
    except Exception as e:
        result["reasons"].append(f"evidence unavailable: {type(e).__name__}: {e}")
    result["record_sha256"]=hashlib.sha256(json.dumps(result,sort_keys=True,default=str).encode()).hexdigest()
    print(json.dumps(result,indent=2,default=str))

def inject(kind):
    with connect(TARGET) as dst:
        if kind=="schema": dst.execute("ALTER TABLE ledger_entries ADD COLUMN divergent TEXT")
        elif kind=="corruption": dst.execute("UPDATE ledger_entries SET amount=amount+1 WHERE id=(SELECT min(id) FROM ledger_entries)")
        elif kind=="sequence": dst.execute("SELECT setval(pg_get_serial_sequence('ledger_entries','id'),1,true)")
    print("Injected target fault:",kind)

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("setup")
    s=sub.add_parser("seed");s.add_argument("count",type=int)
    sub.add_parser("fence");sub.add_parser("sync-sequence");sub.add_parser("assess")
    s=sub.add_parser("inject");s.add_argument("kind",choices=["schema","corruption","sequence"])
    args=p.parse_args()
    if args.command=="setup": setup()
    elif args.command=="seed": seed(args.count)
    elif args.command=="fence": fence()
    elif args.command=="sync-sequence": sync_sequence()
    elif args.command=="assess": assess()
    elif args.command=="inject": inject(args.kind)

if __name__=="__main__":main()
