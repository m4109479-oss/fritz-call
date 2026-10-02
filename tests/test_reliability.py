import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.call_manager import CallManager
from app.csv_sync import CsvSync
from app.customer_lookup import CustomerLookup
from app.eventbus import EVENT_BUS
from app.fritzbox import FritzBoxListener
from app.history import CallHistory
from app.runtime_status import RUNTIME_STATUS, RuntimeStatus
from app.sync_worker import SyncWorker


class CustomerTests(unittest.TestCase):
    def test_international_german_formats_match_domestic_number(self):
        lookup = CustomerLookup.__new__(CustomerLookup)
        for number in ("+49 561 123456", "0049 561 123456", "0561 / 123456", "+49 (0) 561 123456"):
            with self.subTest(number=number):
                self.assertEqual(lookup.normalize_phone(number), "0561123456")
        self.assertEqual(lookup.normalize_phone("+43 1 2345678"), "4312345678")
        self.assertEqual(lookup.normalize_phone(""), "")

    def test_missing_and_invalid_csv_keep_previous_customer_index(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "Export.csv"
            lookup = CustomerLookup(filename)
            self.assertEqual(lookup.find("0561123456"), "unbekannt")
            filename.write_text("Zuname;Vorname;Telefon1\nBeispiel;Erika;0561123456\n")
            self.assertTrue(lookup.reload())
            self.assertEqual(lookup.find("0049561123456"), "Beispiel, Erika")
            filename.write_text("falsche;Spalten\n")
            self.assertFalse(lookup.reload())
            filename.unlink()
            self.assertEqual(lookup.find("0561123456"), "Beispiel, Erika")


class CallTests(unittest.TestCase):
    def setUp(self):
        self.manager = CallManager()
        self.listener = FritzBoxListener(self.manager, SimpleNamespace(find=lambda _: "Beispiel"), "fritz.box", 1012)

    def test_zero_second_connected_call_is_answered(self):
        self.listener.handle_event({"event": "RING", "id": "1", "number": "012345"})
        self.listener.handle_event({"event": "CONNECT", "id": "1", "extension": "2"})
        self.listener.handle_event({"event": "DISCONNECT", "id": "1", "duration": "0"})
        self.assertEqual(self.manager.get_history()[0]["status"], "answered")
        self.assertEqual(self.manager.get_history()[0]["extension"], "2")

    def test_history_is_available_when_disconnect_is_published(self):
        received = []
        def observe(event):
            received.append((event["status"], len(self.manager.get_history())))
        EVENT_BUS.subscribe(observe)
        try:
            self.manager.add_call({"id": "1", "event": "DISCONNECT", "duration": 0})
        finally:
            EVENT_BUS.unsubscribe(observe)
        self.assertEqual(received, [("missed", 1)])

    def test_snapshots_do_not_mutate_after_publication(self):
        original = {"event": "RING", "id": "1"}
        self.manager.add_call(original)
        original["event"] = "DISCONNECT"
        copy = self.manager.get_current()
        copy[0]["event"] = "CONNECT"
        self.assertEqual(self.manager.get_current()[0]["event"], "RING")

    def test_connection_loss_clears_only_live_calls(self):
        self.listener.handle_event({"event": "RING", "id": "1", "number": "012345"})
        RUNTIME_STATUS.set_fritz(True)
        self.listener.connection_lost()
        self.assertEqual(self.manager.get_current(), [])
        self.assertEqual(self.manager.get_history(), [])
        self.assertFalse(RUNTIME_STATUS.snapshot()["fritz_connected"])

    def test_parallel_calls_and_reused_ids_remain_independent(self):
        for call_id in ("1", "2"):
            self.listener.handle_event({"event": "RING", "id": call_id, "number": "012345"})
        self.listener.handle_event({"event": "DISCONNECT", "id": "1", "duration": 0})
        self.assertEqual([call["id"] for call in self.manager.get_current()], ["2"])
        self.listener.handle_event({"event": "RING", "id": "1", "number": "067890"})
        self.assertEqual(len(self.manager.get_current()), 2)
        self.assertEqual(self.manager.get_history()[0]["number"], "012345")

    def test_malformed_and_outgoing_events_are_ignored(self):
        for line in ("garbage", "date;CALL;1;2;3", "date;DISCONNECT;1;invalid", "date;RING;;1;2"):
            self.assertIsNone(self.listener.parse_event(line))
        self.assertEqual(self.listener.parse_event("date;CONNECT;1;2;012345;")["extension"], "2")


class HistoryTests(unittest.TestCase):
    def test_persistence_and_retention_survive_restarts(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "calls.sqlite3"
            history = CallHistory(2, filename)
            for number in range(3):
                history.add({"id": number, "customer": "Stückrath"})
            history.close()
            restored = CallHistory(2, filename)
            self.assertEqual([call["id"] for call in restored.get_all()], [2, 1])
            self.assertEqual(restored.database.execute("SELECT COUNT(*) FROM calls").fetchone()[0], 2)
            restored.close()


class CsvSyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.filename = Path(self.directory.name) / "Export.csv"
        self.old = b"Zuname;Telefon1\nAlt;0561123456\n"
        self.filename.write_bytes(self.old)
        self.sync = CsvSync({"plusfakt": {"server": "example", "share": "data", "path": "Export.csv"},
                             "customer": {"csv_file": str(self.filename)}})

    def run_sync(self, content, after=None, failure=None):
        stat = SimpleNamespace(st_mtime=1700000000, st_size=len(content))
        with patch("app.csv_sync.smbclient.register_session"), \
             patch("app.csv_sync.smbclient.stat", side_effect=[stat, after or stat]), \
             patch("app.csv_sync.smbclient.open_file", return_value=io.BytesIO(content)), \
             patch("app.csv_sync.shutil.copyfileobj", side_effect=failure, wraps=__import__("shutil").copyfileobj):
            self.sync.sync()

    def test_good_download_preserves_source_timestamp(self):
        content = b"Zuname;Telefon1\nNeu;0561123456\n"
        self.run_sync(content)
        self.assertEqual(self.filename.read_bytes(), content)
        self.assertEqual(os.stat(self.filename).st_mtime, 1700000000)
        self.assertEqual(RUNTIME_STATUS.snapshot()["sync"]["state"], "ok")

    def test_invalid_csv_does_not_replace_last_export(self):
        with self.assertRaises(ValueError):
            self.run_sync(b"wrong;header\n")
        self.assertEqual(self.filename.read_bytes(), self.old)
        self.assertEqual(list(Path(self.directory.name).glob(".export-*")), [])
        self.assertEqual(RUNTIME_STATUS.snapshot()["sync"]["state"], "error")

    def test_truncated_row_does_not_replace_last_export(self):
        with self.assertRaises(ValueError):
            self.run_sync(b"Zuname;Telefon1\nBroken\n")
        self.assertEqual(self.filename.read_bytes(), self.old)

    def test_download_failure_does_not_replace_last_export(self):
        with self.assertRaises(OSError):
            self.run_sync(self.old, failure=OSError("network interrupted"))
        self.assertEqual(self.filename.read_bytes(), self.old)
        self.assertEqual(list(Path(self.directory.name).glob(".export-*")), [])

    def test_source_changed_during_transfer_keeps_last_export(self):
        with self.assertRaises(ValueError):
            self.run_sync(self.old, after=SimpleNamespace(st_mtime=1700000001, st_size=len(self.old)))
        self.assertEqual(self.filename.read_bytes(), self.old)


class RuntimeTests(unittest.TestCase):
    def test_sync_errors_keep_last_success_timestamp(self):
        status = RuntimeStatus()
        status.set_sync("ok")
        timestamp = status.snapshot()["sync"]["last_success_at"]
        status.set_sync("error")
        self.assertEqual(status.snapshot()["sync"]["last_success_at"], timestamp)

    def test_failed_sync_retries_without_waiting_full_refresh_interval(self):
        sync = SimpleNamespace(sync=lambda: (_ for _ in ()).throw(OSError("offline")))
        worker = SyncWorker(sync, lambda: True, hours=2)
        with patch.object(worker.stop_event, "wait", return_value=True) as wait:
            worker.run()
        wait.assert_called_once_with(60)


if __name__ == "__main__":
    unittest.main()
