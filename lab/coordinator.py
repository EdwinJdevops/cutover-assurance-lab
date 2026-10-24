"""Fail-closed durable cutover coordinator, research-only. SQLite is a local test journal, not distributed consensus."""
import argparse
import json
import sqlite3
from datetime import datetime, timezone

STATES = ("PREPARED", "FENCED", "VERIFIED", "PROMOTED", "ABORTED")
TRANSITIONS = {
    "PREPARED": {"FENCED", "ABORTED"},
    "FENCED": {"VERIFIED", "ABORTED"},
    "VERIFIED": {"PROMOTED", "ABORTED"},
    "PROMOTED": set(),
    "ABORTED": set(),
}

def connect(path):
    db = sqlite3.connect(path, isolation_level=None, timeout=10)
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS cutovers(
        cutover_id TEXT PRIMARY KEY,
        state TEXT NOT NULL,
        revision INTEGER NOT NULL,
        evidence_json TEXT,
        updated_at TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS events(
        cutover_id TEXT NOT NULL,
        revision INTEGER NOT NULL,
        previous_state TEXT,
        next_state TEXT NOT NULL,
        PRIMARY KEY(cutover_id,revision)
    )""")
    return db

def now():
    return datetime.now(timezone.utc).isoformat()

def initialize(db, key):
    db.execute("BEGIN IMMEDIATE")
    try:
        row=db.execute("SELECT state,revision FROM cutovers WHERE cutover_id=?", (key,)).fetchone()
        if row is None:
            db.execute("INSERT INTO cutovers VALUES(?,?,?,?,?)",(key,"PREPARED",0,None,now()))
            db.execute("INSERT INTO events VALUES(?,?,?,?)",(key,0,None,"PREPARED"))
            row=("PREPARED",0)
        db.execute("COMMIT")
        return row
    except Exception:
        db.execute("ROLLBACK")
        raise

def transition(db,key,expected_revision,next_state,evidence=None, *, _checkpoint=lambda stage: None):
    if next_state not in STATES:
        raise ValueError("unknown state")
    db.execute("BEGIN IMMEDIATE")
    try:
        row=db.execute("SELECT state,revision FROM cutovers WHERE cutover_id=?", (key,)).fetchone()
        if row is None:
            raise ValueError("unknown cutover")
        state,rev=row
        if rev != expected_revision:
            raise ValueError("stale revision")
        if next_state not in TRANSITIONS[state]:
            raise ValueError("forbidden transition")
        if next_state=="VERIFIED":
            if not isinstance(evidence,dict) or evidence.get("decision")!="UNKNOWN":
                raise ValueError("missing baseline assessment")
            # UNKNOWN does not prove readiness; never promote from this evidence.
            raise ValueError("no independently verified cutover barrier")
        if next_state=="PROMOTED":
            raise ValueError("promotion disabled until barrier and external fencing are proven")
        rev+=1
        db.execute("UPDATE cutovers SET state=?,revision=?,evidence_json=?,updated_at=? WHERE cutover_id=?",
                   (next_state,rev,json.dumps(evidence,sort_keys=True) if evidence else None,now(),key))
        _checkpoint("after_update")
        db.execute("INSERT INTO events VALUES(?,?,?,?)",(key,rev,state,next_state))
        _checkpoint("after_event")
        db.execute("COMMIT")
        _checkpoint("after_commit")
        return next_state,rev
    except Exception:
        db.execute("ROLLBACK")
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="coordinator.sqlite3")
    p.add_argument("command",choices=["init","show","fence","abort","promote"])
    p.add_argument("cutover_id")
    p.add_argument("--revision",type=int,default=0)
    a=p.parse_args()
    with connect(a.db) as db:
        if a.command=="init": print(initialize(db,a.cutover_id))
        elif a.command=="show": print(db.execute("SELECT state,revision FROM cutovers WHERE cutover_id=?",(a.cutover_id,)).fetchone())
        else:
            target={"fence":"FENCED","abort":"ABORTED","promote":"PROMOTED"}[a.command]
            print(transition(db,a.cutover_id,a.revision,target))

if __name__=="__main__": main()
