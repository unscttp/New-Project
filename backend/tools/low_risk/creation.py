from typing import Optional

from pydantic import BaseModel, Field

from ..shared.audit import record_audit_event, sha256_text
from ..shared.pathing import resolve_scoped_path


class SaveReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")
    content: str = Field(..., description="要写入文件的文本内容。")


def save_report_file(allowed_folder: str, filename: str, content: str) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    before_hash: Optional[str] = sha256_text(target_path.read_text(encoding="utf-8")) if target_path.exists() else None
    target_path.write_text(content, encoding="utf-8")
    record_audit_event("save_report_file", str(target_path.parent), "authorized", "allow", target_file=target_path.name, details={"checksum_before": before_hash, "checksum_after": sha256_text(content)})
    return f"文件已保存：{target_path}"
