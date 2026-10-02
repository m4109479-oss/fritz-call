import json
import sqlite3
import threading
from collections import deque
from pathlib import Path


class CallHistory:
    """Bounded history, optionally retained in the mounted data directory."""

    def __init__(self, size=1000, filename=None):
        self.size = max(1, int(size))
        self.calls = deque(maxlen=self.size)
        self.lock = threading.RLock()
        self.database = None
        if filename:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            self.database = sqlite3.connect(filename, check_same_thread=False)
            self.database.execute(
                "CREATE TABLE IF NOT EXISTS calls "
                "(sequence INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)"
            )
            self.calls.extend(
                json.loads(row[0]) for row in self.database.execute(
                    "SELECT payload FROM calls ORDER BY sequence DESC LIMIT ?",
                    (self.size,),
                )
            )
            self._prune()
            self.database.commit()

    def _prune(self):
        self.database.execute(
            "DELETE FROM calls WHERE sequence NOT IN "
            "(SELECT sequence FROM calls ORDER BY sequence DESC LIMIT ?)",
            (self.size,),
        )

    def add(self, call):
        snapshot = dict(call)
        with self.lock:
            if self.database:
                with self.database:
                    self.database.execute(
                        "INSERT INTO calls (payload) VALUES (?)",
                        (json.dumps(snapshot, ensure_ascii=False),),
                    )
                    self._prune()
            self.calls.appendleft(snapshot)

    def get_all(self):
        with self.lock:
            return [dict(call) for call in self.calls]

    def close(self):
        with self.lock:
            if self.database:
                self.database.close()
                self.database = None
