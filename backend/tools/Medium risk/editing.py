from typing import Callable


def edit_report_file(
    allowed_folder: str,
    filename: str,
    content: str,
    *,
    resolve_scoped_path: Callable[[str, str], object],
    scoped_path_denied_text: str,
    sha256_text: Callable[[str], str],
    record_audit_event: Callable[..., None],
) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(scoped_path_denied_text)

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
