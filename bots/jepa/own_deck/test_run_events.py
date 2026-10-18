"""Temporary-file event-feed contracts; no training or dashboard service."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_events import RunEvents, SCHEMA, digest_json

COMMIT = "a" * 40


class RunEventContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "events.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def writer(self, run_id="test-run", **changes):
        kwargs = dict(path=self.path, run_id=run_id, commit=COMMIT,
                      config={"objective": "synthetic-test", "nested": {"batch": 2}},
                      dataset={"status": "synthetic", "hashes": ["b" * 64]},
                      limitations=["Temporary logging test; no model or training."])
        kwargs.update(changes)
        return RunEvents(**kwargs)

    def read(self):
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def check_record(self, record):
        schema = json.loads((HERE / "run-events.schema.json").read_text())
        self.assertTrue(set(schema["required"]).issubset(record))
        self.assertEqual(record["schema"], SCHEMA)
        self.assertEqual(record["event_id"], f'{record["run_id"]}:{record["sequence"]}')
        self.assertEqual(record["config_sha256"], digest_json(record["config"]))
        self.assertRegex(record["commit"], "^[0-9a-f]{40}$")
        self.assertEqual(record["heartbeat_at"], record["timestamp"])

    def test_append_and_heartbeat_preserve_previous_bytes_and_current_progress(self):
        writer = self.writer()
        writer.emit("status", "test", 0, status="started")
        prefix = self.path.read_bytes()
        writer.emit("metric", "test", 3, metrics={"measured_items": 3, "fraction": 0.5})
        heartbeat = writer.heartbeat()
        self.assertTrue(self.path.read_bytes().startswith(prefix))
        records = self.read()
        self.assertEqual([r["sequence"] for r in records], [1, 2, 3])
        self.assertEqual((heartbeat["kind"], heartbeat["phase"], heartbeat["step"]),
                         ("heartbeat", "test", 3))
        for record in records:
            self.check_record(record)

    def test_caller_mutations_cannot_change_snapshotted_provenance(self):
        config = {"nested": {"batch": 2}}
        dataset = {"hashes": ["b" * 64]}
        limitations = ["synthetic"]
        writer = self.writer(config=config, dataset=dataset, limitations=limitations)
        config["nested"]["batch"] = 99
        dataset["hashes"].append("c" * 64)
        limitations.append("changed outside logger")
        event = writer.emit("status", "test", 0)
        self.assertEqual(event["config"], {"nested": {"batch": 2}})
        self.assertEqual(event["dataset"], {"hashes": ["b" * 64]})
        self.assertEqual(event["limitations"], ["synthetic"])
        self.check_record(event)

    def test_returned_record_cannot_poison_future_provenance(self):
        writer = self.writer()
        first = writer.emit("status", "test", 0)
        expected = copy.deepcopy(first)
        first["config"]["nested"]["batch"] = 99
        first["dataset"]["hashes"].append("c" * 64)
        first["limitations"].append("mutated returned record")
        second = writer.emit("metric", "test", 1)
        for key in ("config", "dataset", "limitations"):
            self.assertEqual(second[key], expected[key])
        self.check_record(second)

    def test_resume_sequence_and_heartbeat_restore_last_committed_progress(self):
        self.writer().emit("metric", "test-fit", 17, metrics={"measured_items": 17})
        resumed = self.writer()
        event = resumed.heartbeat()
        self.assertEqual(event["sequence"], 2)
        self.assertEqual((event["phase"], event["step"]), ("test-fit", 17))
        self.assertEqual([r["sequence"] for r in self.read()], [1, 2])

    def test_resume_rejects_different_configuration_or_commit_for_same_run(self):
        self.writer().emit("status", "test", 0)
        with self.assertRaises(ValueError):
            self.writer(config={"different": True})
        with self.assertRaises(ValueError):
            self.writer(commit="b" * 40)
        with self.assertRaises(ValueError):
            self.writer(dataset={"status": "different-dataset"})

    def test_short_writes_are_completed_before_publishing_the_record(self):
        writer = self.writer()
        original_open = Path.open
        writes = []

        class ShortWriter:
            def __init__(self, raw):
                self.raw = raw

            def __getattr__(self, name):
                return getattr(self.raw, name)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self.raw.__exit__(*args)

            def write(self, data):
                writes.append(len(data))
                return self.raw.write(data[:7])

        def limited_open(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return ShortWriter(stream) if path == self.path and args and args[0] == "a+b" else stream

        with mock.patch.object(Path, "open", limited_open):
            writer.emit("status", "test", 0)
        self.assertGreater(len(writes), 1)
        records = self.read()
        self.assertEqual(len(records), 1)
        self.check_record(records[0])

    def test_partial_tail_is_preserved_and_new_complete_record_is_separate(self):
        self.writer().emit("status", "test", 0)
        with self.path.open("ab") as stream:
            stream.write(b'{"run_id":"crashed",')
        prefix = self.path.read_bytes()
        self.writer("new-test-run").emit("status", "test", 0)
        self.assertTrue(self.path.read_bytes().startswith(prefix))
        lines = self.path.read_text().splitlines()
        self.assertEqual(len(lines), 3)
        with self.assertRaises(ValueError):
            json.loads(lines[1])
        self.assertEqual(json.loads(lines[2])["run_id"], "new-test-run")

    def test_non_event_json_lines_do_not_break_resume_scan(self):
        self.path.write_text('null\n[]\n42\n"other-json"\n')
        writer = self.writer()
        event = writer.emit("status", "test", 0)
        self.assertEqual(event["sequence"], 1)

    def test_nonfinite_metrics_and_nested_payloads_are_rejected(self):
        writer = self.writer()
        writer.emit("status", "test", 0)
        prefix = self.path.read_bytes()
        for value in (float("nan"), float("inf"), -float("inf"), True, "1"):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                writer.emit("metric", "test", 1, metrics={"value": value})
            self.assertEqual(self.path.read_bytes(), prefix)
        with self.assertRaises(ValueError):
            writer.emit("artifact", "test", 1, artifacts={"nested": [float("nan")]})
        self.assertEqual(self.path.read_bytes(), prefix)
        with self.assertRaises(ValueError):
            self.writer("invalid-config", config={"value": float("nan")})

    def test_invalid_kind_step_and_reserved_provenance_are_rejected(self):
        writer = self.writer()
        for value in (-1, 1.5, True):
            with self.subTest(step=value), self.assertRaises(ValueError):
                writer.emit("status", "test", value)
        with self.assertRaises(ValueError):
            writer.emit("invented-kind", "test", 0)
        with self.assertRaises(ValueError):
            writer.emit("status", "test", 0, config_sha256="c" * 64)
        self.assertFalse(self.path.exists())

    def test_different_process_run_ids_append_parseable_independent_sequences(self):
        code = """import sys
sys.path.insert(0,sys.argv[1])
from run_events import RunEvents
w=RunEvents(sys.argv[2],sys.argv[3],'a'*40,{'purpose':'synthetic logging test'},
            {'status':'synthetic'},['Temporary logging test; no training.'])
for i in range(12): w.emit('metric','test',i,metrics={'measured_items':i})
"""
        children = []
        try:
            for run_id in ("process-a", "process-b", "process-c"):
                children.append(subprocess.Popen(
                    [sys.executable, "-c", code, str(HERE), str(self.path), run_id],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            for child in children:
                stdout, stderr = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, stdout + stderr)
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
                    child.communicate(timeout=5)
        records = self.read()
        self.assertEqual(len(records), 36)
        for run_id in ("process-a", "process-b", "process-c"):
            own = [r for r in records if r["run_id"] == run_id]
            self.assertEqual([r["sequence"] for r in own], list(range(1, 13)))
            self.assertEqual([r["step"] for r in own], list(range(12)))
        self.assertEqual(len({r["event_id"] for r in records}), 36)
        for record in records:
            self.check_record(record)


if __name__ == "__main__":
    unittest.main()
