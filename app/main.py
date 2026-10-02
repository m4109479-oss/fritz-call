import logging
import threading
from pathlib import Path

import uvicorn

from app.config import load_config
from app.csv_sync import CsvSync
from app.sync_worker import SyncWorker
from app.customer_lookup import CustomerLookup
from app.fritzbox import FritzBoxListener
from app.state import CALL_MANAGER


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    history = config.get("history", {})
    CALL_MANAGER.configure_history(
        history.get("file", str(Path(config["customer"]["csv_file"]).parent / "calls.sqlite3")),
        history.get("size", 1000),
    )
    customers = CustomerLookup(config["customer"]["csv_file"])
    worker = SyncWorker(CsvSync(config), customers.reload, config["plusfakt"]["refresh_hours"])
    worker.start()
    fritz = FritzBoxListener(
        CALL_MANAGER, customers, config["fritzbox"]["ip"], config["fritzbox"]["port"],
    )
    threading.Thread(target=fritz.start, daemon=True).start()
    try:
        uvicorn.run("app.api:app", host="0.0.0.0", port=8000, log_level="info")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
