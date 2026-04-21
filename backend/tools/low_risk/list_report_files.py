import json
from pathlib import Path
from typing import Callable, Set


def list_report_files(
    allowed_folder: str,
    *,
    assert_access_granted_and_scoped: Callable[[str], Path],
    allowed_report_extensions: Set[str],
) -> str:
    report_dir = assert_access_granted_and_scoped(allowed_folder)
    files = sorted(
        [
            item.name
            for item in report_dir.iterdir()
            if item.is_file() and item.suffix.lower() in allowed_report_extensions
        ]
    )
    return json.dumps(
        {"allowed_folder": str(report_dir), "files": files},
        ensure_ascii=False,
        indent=2,
    )
