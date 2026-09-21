import unittest
from unittest.mock import patch

from app.call_manager import CallManager
from app.fritzbox import FritzBoxListener


class CustomerLookupStub:

    def find(self, number):
        return "Beispiel, Erika"


class CurrentCallTests(unittest.TestCase):

    def setUp(self):
        self.call_manager = CallManager()
        self.listener = FritzBoxListener(
            self.call_manager,
            CustomerLookupStub(),
            "fritz.box",
            1012
        )

    @patch("app.fritzbox.time.time", side_effect=[1000.0, 1010.0])
    def test_active_call_keeps_ring_and_connect_timestamps(self, _time):
        self.listener.handle_event({
            "event": "RING",
            "id": "7",
            "number": "012345",
            "target": "98765",
            "time": "21.09.26 10:00:00"
        })
        self.listener.handle_event({
            "event": "CONNECT",
            "id": "7",
            "time": "21.09.26 10:00:10"
        })

        self.assertEqual(
            self.call_manager.get_current(),
            [{
                "event": "CONNECT",
                "id": "7",
                "number": "012345",
                "target": "98765",
                "time": "21.09.26 10:00:00",
                "customer": "Beispiel, Erika",
                "started_at": 1000.0,
                "connected_at": 1010.0
            }]
        )

    @patch("app.fritzbox.time.time", return_value=1000.0)
    def test_disconnect_removes_current_call(self, _time):
        self.listener.handle_event({
            "event": "RING",
            "id": "7",
            "number": "012345",
            "target": "98765",
            "time": "21.09.26 10:00:00"
        })
        self.listener.handle_event({
            "event": "DISCONNECT",
            "id": "7",
            "duration": "0",
            "time": "21.09.26 10:00:20"
        })

        self.assertEqual(self.call_manager.get_current(), [])


if __name__ == "__main__":
    unittest.main()
