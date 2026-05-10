from pydantic import BaseModel, Field


class EditReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")
    content: str = Field(..., description="编辑后完整内容（覆盖写入）。")


def edit_report_file(
    allowed_folder: str,
    filename: str,
    content: str,
) -> str:
    from ..shared.pathing import resolve_scoped_path, SCOPED_PATH_DENIED_TEXT
    from ..shared.audit import record_audit_event, sha256_text
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)

    before_text = target_path.read_text(encoding="utf-8")
    before_hash = sha256_text(before_text)
    target_path.write_text(content, encoding="utf-8")
    after_hash = sha256_text(content)
    record_audit_event(
        operation="edit_report_file",
        target_file=target_path.name,
        allowed_folder=str(target_path.parent),
        authorization_state="authorized",
        decision="allow",
        details={"checksum_before": before_hash, "checksum_after": after_hash},
    )
    return f"文件已更新：{target_path}"
