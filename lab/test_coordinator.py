"""Deterministic coordinator crash and concurrency regression tests."""
import os
import pathlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
import subprocess
import sys
import time
from coordinator import connect,initialize,transition

class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=str(pathlib.Path(self.tmp.name)/"state.sqlite3")
        self.db=connect(self.path)
        self.assertEqual(initialize(self.db,"cutover-1"),("PREPARED",0))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_killed_process_recovers_atomic_journal(self):
        for stage, expected in (("after_update",("PREPARED",0)),
                                ("after_event",("PREPARED",0)),
                                ("after_commit",("FENCED",1))):
            with self.subTest(stage=stage):
                path = str(pathlib.Path(self.tmp.name)/(stage+".sqlite3"))
                signal = pathlib.Path(self.tmp.name)/(stage+".ready")
                child = """
import pathlib,sys,time
from coordinator import connect,initialize,transition
db=connect(sys.argv[1])
initialize(db,"crash")
def checkpoint(stage):
    if stage==sys.argv[2]:
        pathlib.Path(sys.argv[3]).write_text(stage)
        time.sleep(60)
transition(db,"crash",0,"FENCED",_checkpoint=checkpoint)
"""
                proc=subprocess.Popen([sys.executable,"-c",child,path,stage,str(signal)],
                                      cwd=pathlib.Path(__file__).parent)
                try:
                    deadline=time.monotonic()+15
                    while not signal.exists():
                        if proc.poll() is not None or time.monotonic()>deadline:
                            self.fail("child did not reach crash checkpoint")
                        time.sleep(.02)
                    proc.kill()  # SIGKILL on CI; TerminateProcess on Windows.
                    proc.wait(timeout=10)
                    with closing(connect(path)) as recovered:
                        self.assertEqual(recovered.execute("PRAGMA integrity_check").fetchone(),("ok",))
                        self.assertEqual(initialize(recovered,"crash"),expected)
                        events=recovered.execute("SELECT revision,next_state FROM events ORDER BY revision").fetchall()
                        self.assertEqual(events,[(0,"PREPARED")]+([(1,"FENCED")] if expected[1] else []))
                        if expected[1]:
                            with self.assertRaisesRegex(ValueError,"stale revision"):
                                transition(recovered,"crash",0,"FENCED")
                        else:
                            self.assertEqual(transition(recovered,"crash",0,"FENCED"),("FENCED",1))
                        with self.assertRaises(ValueError):
                            transition(recovered,"crash",1,"VERIFIED",{"decision":"UNKNOWN"})
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=10)

    def test_competing_processes_only_one_revision_wins(self):
        child = """
import sys
from coordinator import connect,transition
try:
    with connect(sys.argv[1]) as db:
        transition(db,"cutover-1",0,sys.argv[2])
except ValueError:
    sys.exit(2)
"""
        processes=[subprocess.Popen([sys.executable,"-c",child,self.path,state],
                   cwd=pathlib.Path(__file__).parent) for state in ("FENCED","ABORTED")]
        try:
            self.assertEqual(sorted(p.wait(timeout=15) for p in processes),[0,2])
            self.assertEqual(self.db.execute("SELECT revision FROM cutovers").fetchone(),(1,))
            self.assertEqual(self.db.execute("SELECT count(*) FROM events").fetchone(),(2,))
        finally:
            for p in processes:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=10)

    def test_restart_preserves_fenced_state(self):
        self.assertEqual(transition(self.db,"cutover-1",0,"FENCED"),("FENCED",1))
        self.db.close()
        self.db=connect(self.path)
        self.assertEqual(initialize(self.db,"cutover-1"),("FENCED",1))

    def test_stale_revision_cannot_replay_transition(self):
        transition(self.db,"cutover-1",0,"FENCED")
        with self.assertRaisesRegex(ValueError,"stale revision"):
            transition(self.db,"cutover-1",0,"ABORTED")
        self.assertEqual(self.db.execute("SELECT state FROM cutovers").fetchone()[0],"FENCED")

    def test_promotion_always_refused(self):
        with self.assertRaisesRegex(ValueError,"forbidden transition"):
            transition(self.db,"cutover-1",0,"PROMOTED")
        transition(self.db,"cutover-1",0,"FENCED")
        with self.assertRaisesRegex(ValueError,"no independently verified cutover barrier"):
            transition(self.db,"cutover-1",1,"VERIFIED",{"decision":"UNKNOWN"})
        self.assertEqual(self.db.execute("SELECT state FROM cutovers").fetchone()[0],"FENCED")

    def test_abort_is_terminal_and_idempotent_init(self):
        self.assertEqual(transition(self.db,"cutover-1",0,"ABORTED"),("ABORTED",1))
        self.assertEqual(initialize(self.db,"cutover-1"),("ABORTED",1))
        with self.assertRaisesRegex(ValueError,"forbidden transition"):
            transition(self.db,"cutover-1",1,"FENCED")

    def test_atomic_rollback_on_failed_transition(self):
        with self.assertRaises(ValueError):
            transition(self.db,"cutover-1",0,"VERIFIED")
        self.assertEqual(self.db.execute("SELECT count(*) FROM events").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT revision FROM cutovers").fetchone()[0],0)

if __name__=="__main__":
    unittest.main()
