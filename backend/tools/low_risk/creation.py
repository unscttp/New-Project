from typing import Callable, Optional


def save_report_file(
    allowed_folder: str,
    filename: str,
    content: str,
    *,
    resolve_scoped_path: Callable[[str, str], object],
    sha256_text: Callable[[str], str],
    record_audit_event: Callable[..., None],
) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    before_hash: Optional[str] = (
        sha256_text(target_path.read_text(encoding="utf-8")) if target_path.exists() else None
    )
    target_path.write_text(content, encoding="utf-8")
    after_hash = sha256_text(content)
    record_audit_event(
        operation="save_report_file",
        target_file=target_path.name,
        allowed_folder=str(target_path.parent),
        authorization_state="authorized",
        decision="allow",
        details={"checksum_before": before_hash, "checksum_after": after_hash},
    )
    return f"文件已保存：{target_path}"
