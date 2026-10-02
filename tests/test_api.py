import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import app
from app.call_manager import CallManager
from app.runtime_status import RuntimeStatus


class ApiTests(unittest.TestCase):
    def test_status_reports_real_fritz_connection(self):
        runtime = RuntimeStatus()
        with patch("app.api.RUNTIME_STATUS", runtime), \
             patch("app.api.get_export_modified_at", return_value=None):
            with TestClient(app) as client:
                self.assertFalse(client.get("/status").json()["online"])
                runtime.set_fritz(True)
                self.assertTrue(client.get("/status").json()["online"])
                response = client.get("/")
                self.assertEqual(response.status_code, 200)
                self.assertIn("© Michel Stückrath 2026", response.text)

    def test_history_and_websocket_receive_completed_call(self):
        manager = CallManager()
        with patch("app.api.CALL_MANAGER", manager):
            with TestClient(app) as client:
                with client.websocket_connect("/ws") as websocket:
                    manager.add_call({"event": "DISCONNECT", "id": "1", "duration": 0})
                    event = websocket.receive_json()
                    self.assertEqual(event["status"], "missed")
                    self.assertEqual(client.get("/history").json()["count"], 1)
