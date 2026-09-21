import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.export_info import get_export_modified_at


class ExportTimestampTests(unittest.TestCase):

    def test_returns_csv_modification_time_as_utc_iso_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_file = Path(directory) / "Export.csv"
            csv_file.write_text("Zuname;Vorname\n", encoding="utf-8")
            os.utime(csv_file, (1_700_000_000, 1_700_000_000))

            result = get_export_modified_at(csv_file)

        self.assertEqual(
            result,
            datetime.fromtimestamp(
                1_700_000_000,
                timezone.utc
            ).isoformat()
        )

    def test_returns_none_when_csv_does_not_exist(self):
        self.assertIsNone(
            get_export_modified_at(
                "/does/not/exist.csv"
            )
        )


if __name__ == "__main__":
    unittest.main()
