import csv
import logging
import os
import shutil
import tempfile
from pathlib import Path

import smbclient

from app.customer_lookup import validate_reader
from app.runtime_status import RUNTIME_STATUS

logger = logging.getLogger(__name__)


class CsvSync:
    def __init__(self, config):
        self.config = config

    def sync(self):
        RUNTIME_STATUS.set_sync("syncing")
        temporary = None
        try:
            plusfakt = self.config["plusfakt"]
            server = plusfakt["server"]
            smbclient.register_session(
                server, username=os.getenv("SMB_USERNAME"),
                password=os.getenv("SMB_PASSWORD"),
            )
            remote_file = f"\\\\{server}\\{plusfakt['share']}\\{plusfakt['path']}"
            local_file = Path(self.config["customer"]["csv_file"])
            local_file.parent.mkdir(parents=True, exist_ok=True)
            before = smbclient.stat(remote_file)
            with tempfile.NamedTemporaryFile(
                dir=local_file.parent, prefix=".export-", suffix=".tmp", delete=False,
            ) as dst:
                temporary = Path(dst.name)
                with smbclient.open_file(remote_file, mode="rb") as src:
                    shutil.copyfileobj(src, dst)
                dst.flush()
                os.fsync(dst.fileno())
            after = smbclient.stat(remote_file)
            if before.st_mtime != after.st_mtime or before.st_size != after.st_size:
                raise ValueError("Quellexport hat sich während der Übertragung geändert")
            if temporary.stat().st_size != before.st_size:
                raise ValueError("Export wurde nicht vollständig übertragen")
            with temporary.open(encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file, delimiter=";")
                validate_reader(reader)
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Unvollständige CSV-Zeile")
            os.utime(temporary, (before.st_mtime, before.st_mtime))
            os.replace(temporary, local_file)
            RUNTIME_STATUS.set_sync("ok")
            logger.info("Kundenexport aktualisiert")
        except Exception:
            RUNTIME_STATUS.set_sync("error")
            raise
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
