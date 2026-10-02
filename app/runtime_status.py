import threading
from datetime import datetime, timezone


class RuntimeStatus:
    def __init__(self):
        self.lock = threading.Lock()
        self.fritz_connected = False
        self.sync = {"state": "pending", "last_success_at": None}

    def set_fritz(self, connected):
        with self.lock:
            self.fritz_connected = connected

    def set_sync(self, state):
        with self.lock:
            self.sync["state"] = state
            if state == "ok":
                self.sync["last_success_at"] = datetime.now(timezone.utc).isoformat()

    def snapshot(self):
        with self.lock:
            return {
                "fritz_connected": self.fritz_connected,
                "sync": dict(self.sync),
            }


RUNTIME_STATUS = RuntimeStatus()
