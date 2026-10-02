import threading

from app.history import CallHistory
from app.eventbus import EVENT_BUS


class CallManager:
    def __init__(self):
        self.history = CallHistory()
        self.current_calls = {}
        self.lock = threading.RLock()

    def configure_history(self, filename, size=1000):
        with self.lock:
            self.history.close()
            self.history = CallHistory(size, filename)

    def add_call(self, call):
        snapshot = dict(call)
        call_id = snapshot.get("id")
        with self.lock:
            if snapshot.get("event") == "DISCONNECT":
                previous = self.current_calls.get(call_id, {})
                snapshot["duration"] = max(0, int(snapshot.get("duration", 0)))
                answered = (
                    snapshot.get("connected_at") is not None
                    or previous.get("event") == "CONNECT"
                    or snapshot["duration"] > 0
                )
                snapshot["status"] = "answered" if answered else "missed"
                self.history.add(snapshot)
                self.current_calls.pop(call_id, None)
            elif call_id is not None:
                self.current_calls[call_id] = snapshot
            # Publish the completed state only after history is available.
            EVENT_BUS.publish(dict(snapshot))

    def clear_current(self):
        with self.lock:
            self.current_calls.clear()
            EVENT_BUS.publish({"event": "RESET"})

    def get_current(self):
        with self.lock:
            return [dict(call) for call in self.current_calls.values()]

    def get_history(self):
        return self.history.get_all()
