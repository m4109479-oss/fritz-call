import logging
import threading

from app.runtime_status import RUNTIME_STATUS

logger = logging.getLogger(__name__)


class SyncWorker:
    def __init__(self, sync, reload_callback, hours=24):
        self.sync = sync
        self.reload_callback = reload_callback
        self.interval = max(60, float(hours) * 3600)
        self.stop_event = threading.Event()

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def stop(self):
        self.stop_event.set()

    def run(self):
        # An unavailable SMB server must not block API or callmonitor startup.
        while not self.stop_event.is_set():
            try:
                self.sync.sync()
                if self.reload_callback() is False:
                    raise ValueError("Kundenexport konnte nicht geladen werden")
                wait = self.interval
            except Exception:
                RUNTIME_STATUS.set_sync("error")
                logger.warning("CSV-Abgleich fehlgeschlagen; erneuter Versuch in 60 Sekunden")
                wait = min(self.interval, 60)
            if self.stop_event.wait(wait):
                return
