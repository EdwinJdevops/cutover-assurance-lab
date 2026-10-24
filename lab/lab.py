"""Disposable PostgreSQL logical replication experiment. Synthetic data only."""
import argparse, hashlib, json, os, sys, uuid
from datetime import datetime, timezone
import psycopg

SOURCE = "postgresql://postgres:labonly@localhost:55432/ledger"
TARGET = "postgresql://postgres:labonly@localhost:55433/ledger"

def connect(dsn):
    return psycopg.connect(dsn, connect_timeout=5, autocommit=True)

def setup():
    with connect(SOURCE) as src, connect(TARGET) as dst:
        src.execute("CREATE PUBLICATION ledger_pub FOR TABLE ledger_entries, cutover_barrier")
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
        with src.transaction():
            src.execute("SET LOCAL lock_timeout='5s'")
            # Drain existing DML before taking the fingerprint and committing the fence.
            src.execute("LOCK TABLE ledger_entries IN SHARE ROW EXCLUSIVE MODE")
            src.execute("UPDATE lab_control SET writes_fenced=TRUE WHERE singleton")
            a = fingerprint(src)
            src.execute("""INSERT INTO cutover_barrier
                (singleton,token,source_txid,ledger_digest,ledger_rows,schema_hash)
                VALUES(TRUE,%s,pg_current_xact_id()::text,%s,%s,%s)
                ON CONFLICT(singleton) DO UPDATE SET token=excluded.token,
                source_txid=excluded.source_txid,ledger_digest=excluded.ledger_digest,
                ledger_rows=excluded.ledger_rows,schema_hash=excluded.schema_hash,
                created_at=clock_timestamp()""",
                (uuid.uuid4(),a["digest"],a["rows"],a["schema_hash"]))
    print("Committed synthetic fence and transaction-linked barrier; not application-wide fencing")


def barrier(conn):
    row = conn.execute("""SELECT token::text,source_txid,ledger_digest,ledger_rows,
        schema_hash,created_at FROM cutover_barrier WHERE singleton""").fetchone()
    if row is None:
        return None
    return dict(zip(("token","source_txid","digest","rows","schema_hash","created_at"),row))


def check_barrier(src, dst, a, b):
    source, target = barrier(src), barrier(dst)
    reasons = []
    if source is None or target is None:
        reasons.append("transaction-linked barrier missing")
    elif source != target:
        reasons.append("transaction-linked barrier mismatch")
    else:
        age = (datetime.now(timezone.utc)-source["created_at"]).total_seconds()
        if not 0 <= age <= 300:
            reasons.append("transaction-linked barrier expired or future dated")
        for data in (a,b):
            if any(source[k] != data[k] for k in ("digest","rows","schema_hash")):
                reasons.append("transaction-linked barrier ledger mismatch")
                break
    return {"source":source,"target":target,"matched":not reasons}, reasons


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
        c.execute("SELECT id,event_id::text,account_id,amount,created_at::text FROM ledger_entries ORDER BY id")
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
            # Each database is internally consistent; this is not a cross-database snapshot.
            src.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            dst.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            a,b=fingerprint(src),fingerprint(dst)
            result["barrier"], barrier_reasons = check_barrier(src,dst,a,b)
            result["reasons"].extend(barrier_reasons)
            result["source"],result["target"]=a,b
            with src.cursor() as c:
                c.execute("SELECT writes_fenced FROM lab_control WHERE singleton")
                fenced=c.fetchone()[0]
                c.execute("SELECT pg_current_wal_lsn()::text")
                result["source_current_lsn"]=c.fetchone()[0]
            with dst.cursor() as c:
                c.execute("SELECT received_lsn::text,latest_end_lsn::text FROM pg_stat_subscription WHERE subname='ledger_sub' AND relid IS NULL AND pid IS NOT NULL")
                subscription=c.fetchone()
            result["target_subscription"]=subscription
            with dst.cursor() as c:
                c.execute("SELECT count(*), count(*) FILTER (WHERE srsubstate='r') FROM pg_subscription_rel WHERE srsubid=(SELECT oid FROM pg_subscription WHERE subname='ledger_sub')")
                table_count,ready_count=c.fetchone()
            result["table_sync"]={"total":table_count,"ready":ready_count}
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
            if table_count != 2 or ready_count != table_count: result["reasons"].append("replicated tables not all ready")
            if not subscription or not subscription[0]: result["reasons"].append("subscription apply worker missing or not reporting received LSN")
            if result["reasons"]: result["decision"]="NO-GO"
            else: result["reasons"].append("missing independently verified application fencing, dependency health, and rollback evidence")
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
