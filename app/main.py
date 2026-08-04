from app.config import load_config
from app.csv_sync import CsvSync
from app.sync_worker import SyncWorker
from app.customer_lookup import CustomerLookup
from app.fritzbox import FritzBoxListener
from app.state import CALL_MANAGER

import threading
import uvicorn


def start_api():

    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


def main():

    print("Fritz-Call startet...")

    config = load_config()

    sync = CsvSync(config)

    sync.sync()

    customers = CustomerLookup(
        config["customer"]["csv_file"]
    )

    worker = SyncWorker(
        sync,
        customers.reload,
        config["plusfakt"]["refresh_hours"]
    )

    worker.start()

    api_thread = threading.Thread(
        target=start_api,
        daemon=True
    )

    api_thread.start()


    fritz = FritzBoxListener(
        CALL_MANAGER,
        customers,
        config["fritzbox"]["ip"],
        config["fritzbox"]["port"]
    )

    fritz_thread = threading.Thread(
        target=fritz.start,
        daemon=True
    )

    fritz_thread.start()

    print("System bereit.")

    fritz_thread.join()


if __name__ == "__main__":
    main()
