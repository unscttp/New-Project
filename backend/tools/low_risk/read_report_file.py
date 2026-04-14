from typing import Callable


def read_report_file(
    allowed_folder: str,
    filename: str,
    *,
    resolve_scoped_path: Callable[[str, str], object],
    scoped_path_denied_text: str,
) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(scoped_path_denied_text)
    return target_path.read_text(encoding="utf-8")
