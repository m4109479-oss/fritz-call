import logging
import socket
import time

from app.runtime_status import RUNTIME_STATUS

logger = logging.getLogger(__name__)


class FritzBoxListener:
    def __init__(self, call_manager, customer_lookup, host, port):
        self.call_manager = call_manager
        self.customer_lookup = customer_lookup
        self.host = host
        self.port = port
        self.active_calls = {}

    def parse_event(self, line):
        parts = line.strip().split(";")
        if len(parts) < 3 or not parts[2]:
            return None
        result = {"time": parts[0], "event": parts[1], "id": parts[2]}
        if parts[1] == "RING" and len(parts) >= 5:
            result.update(number=parts[3], target=parts[4])
        elif parts[1] == "CONNECT":
            if len(parts) >= 4:
                result["extension"] = parts[3]
        elif parts[1] == "DISCONNECT" and len(parts) >= 4:
            try:
                result["duration"] = max(0, int(parts[3]))
            except ValueError:
                return None
        else:
            return None
        return result

    def handle_event(self, event):
        call_id = event.get("id")
        if call_id is None:
            return
        event_type = event["event"]
        if event_type == "RING":
            call = dict(event)
            call["customer"] = self.customer_lookup.find(call.get("number", ""))
            call["started_at"] = time.time()
            self.active_calls[call_id] = call
            self.call_manager.add_call(call)
        elif event_type == "CONNECT":
            call = self.active_calls.get(call_id)
            if call:
                call["connected_at"] = time.time()
                call["event"] = "CONNECT"
                if "extension" in event:
                    call["extension"] = event["extension"]
                self.call_manager.add_call(call)
        elif event_type == "DISCONNECT":
            call = self.active_calls.pop(call_id, None)
            if call:
                call["duration"] = max(0, int(event.get("duration", 0)))
                call["event"] = "DISCONNECT"
                self.call_manager.add_call(call)

    def connection_lost(self):
        RUNTIME_STATUS.set_fritz(False)
        self.active_calls.clear()
        # Lost events cannot be reconstructed; do not invent history entries.
        self.call_manager.clear_current()

    def start(self):
        while True:
            try:
                with socket.create_connection((self.host, self.port), timeout=10) as sock:
                    sock.settimeout(None)  # Quiet periods between calls are normal.
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for option, value in (("TCP_KEEPIDLE", 60), ("TCP_KEEPINTVL", 15), ("TCP_KEEPCNT", 3)):
                        if hasattr(socket, option):
                            sock.setsockopt(socket.IPPROTO_TCP, getattr(socket, option), value)
                    RUNTIME_STATUS.set_fritz(True)
                    logger.info("FRITZ!Box verbunden")
                    with sock.makefile("r", encoding="utf-8", errors="replace") as stream:
                        for line in stream:
                            event = self.parse_event(line)
                            if event:
                                try:
                                    self.handle_event(event)
                                except (ValueError, KeyError, OSError):
                                    logger.exception("Telefonereignis konnte nicht verarbeitet werden")
                    raise ConnectionError("Callmonitor-Verbindung geschlossen")
            except Exception as error:
                logger.warning("FRITZ!Box-Verbindung unterbrochen: %s", error)
            finally:
                self.connection_lost()
            time.sleep(5)
