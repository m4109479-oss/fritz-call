from datetime import datetime, timezone
from pathlib import Path


def get_export_modified_at(csv_filename):

    csv_file = Path(csv_filename)

    try:
        modified = csv_file.stat().st_mtime
    except OSError:
        return None

    return datetime.fromtimestamp(
        modified,
        timezone.utc
    ).isoformat()
