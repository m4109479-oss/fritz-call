import os
import shutil
from pathlib import Path

import smbclient

from app.config import load_config

class CsvSync:

    def __init__(self, config):
        self.config = config


    def sync(self):

        plusfakt = self.config["plusfakt"]

        username = os.getenv("SMB_USERNAME")
        password = os.getenv("SMB_PASSWORD")

        server = plusfakt["server"]

        smbclient.register_session(
            server,
            username=username,
            password=password
        )

        remote_file = (
            f"\\\\{server}\\"
            f"{plusfakt['share']}\\"
            f"{plusfakt['path']}"
        )

        local_file = Path(
            self.config["customer"]["csv_file"]
        )

        print("Lade:")
        print(remote_file)

        local_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with smbclient.open_file(
            remote_file,
            mode="rb"
        ) as src:

            with open(
                local_file,
                "wb"
            ) as dst:

                shutil.copyfileobj(
                    src,
                    dst
                )

        print("Gespeichert:")
        print(local_file)

        print(
            "Größe:",
            local_file.stat().st_size,
            "Bytes"
        )


if __name__ == "__main__":

    config = load_config()

    sync = CsvSync(config)

    sync.sync()
