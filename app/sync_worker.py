import time
import threading


class SyncWorker:

    def __init__(self, sync, reload_callback, hours=24):

        self.sync = sync
        self.reload_callback = reload_callback
        self.interval = hours * 60 * 60
        self.running = True


    def start(self):

        thread = threading.Thread(
            target=self.run,
            daemon=True
        )

        thread.start()


    def run(self):

        time.sleep(self.interval)

        while self.running:

            print("CSV Sync Prüfung")

            try:
                self.sync.sync()
                self.reload_callback()

            except Exception as e:
                print(
                    "CSV Sync Fehler:",
                    e
                )

            time.sleep(self.interval)
