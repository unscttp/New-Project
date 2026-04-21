from pathlib import Path
from typing import Callable


def delete_report_file(
    allowed_folder: str,
    filename: str,
    *,
    resolve_scoped_path: Callable[[str, str], Path],
    record_audit_event: Callable[..., None],
) -> str:
    """删除授权目录中的文件（高风险）。"""
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError("目标不是可删除文件。")

    target_path.unlink()
    record_audit_event(
        operation="delete_report_file",
        target_file=target_path.name,
        allowed_folder=str(target_path.parent),
        authorization_state="authorized",
        decision="allow",
    )
    return f"文件已删除：{target_path}"
