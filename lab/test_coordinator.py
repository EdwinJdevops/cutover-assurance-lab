"""Deterministic coordinator crash and concurrency regression tests."""
import os
import pathlib
import sqlite3
import tempfile
import unittest
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
