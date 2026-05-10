from pydantic import BaseModel, Field

from ..shared.audit import record_audit_event
from ..shared.pathing import resolve_scoped_path


class DeleteReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="要删除的文件名（仅文件名）。")


def delete_report_file(allowed_folder: str, filename: str) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError("目标不是可删除文件。")
    target_path.unlink()
    record_audit_event("delete_report_file", str(target_path.parent), "authorized", "allow", target_file=target_path.name)
    return f"文件已删除：{target_path}"
