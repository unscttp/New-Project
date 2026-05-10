import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .audit import (
    ERROR_CATEGORY_FORMAT_UNSUPPORTED,
    ERROR_CATEGORY_PATH_VIOLATION,
    ERROR_CATEGORY_PERMISSION_DENIED,
    get_active_permission_state,
    record_audit_event,
)

UNAUTHORIZED_FILE_ACCESS_TEXT = "未授权文件访问，请先确认目录和权限。"
SCOPED_PATH_DENIED_TEXT = "目标文件不在授权目录内，操作已拒绝。"
ALLOWED_REPORT_EXTENSIONS = {".md", ".docx", ".pdf"}


def make_safe_stem(stem: str) -> str:
    safe_stem = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", stem).strip("-_")
    return safe_stem or "untitled-report"


def safe_report_path(title: str, report_dir: Path) -> Path:
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{make_safe_stem(title)}.md"
    target_path = (report_dir / filename).resolve()
    if report_dir not in target_path.parents and target_path != report_dir:
        raise ValueError("非法文件路径，已阻止目录穿越。")
    return target_path


def assert_access_granted_and_scoped(allowed_folder: str) -> Path:
    state = get_active_permission_state()
    granted = bool(state.get("file_access_granted"))
    scoped_folder = state.get("allowed_report_folder")
    allowed_folder_text = allowed_folder.strip()
    if not granted or not scoped_folder or not str(scoped_folder).strip():
        record_audit_event(
            operation="permission_check",
            allowed_folder=allowed_folder_text or str(scoped_folder or ""),
            authorization_state="unauthorized",
            decision="deny",
            error_category=ERROR_CATEGORY_PERMISSION_DENIED,
        )
        raise PermissionError(UNAUTHORIZED_FILE_ACCESS_TEXT)

    state_dir = Path(str(scoped_folder)).expanduser().resolve()
    request_dir = Path(allowed_folder_text).expanduser().resolve()
    if request_dir != state_dir:
        record_audit_event(
            operation="permission_check",
            allowed_folder=allowed_folder_text,
            authorization_state="authorized",
            decision="deny",
            error_category=ERROR_CATEGORY_PATH_VIOLATION,
            details={"reason": "folder_not_in_scope"},
        )
        raise PermissionError(UNAUTHORIZED_FILE_ACCESS_TEXT)

    state_dir.mkdir(parents=True, exist_ok=True)
    record_audit_event("permission_check", str(state_dir), "authorized", "allow")
    return state_dir


def resolve_scoped_path(allowed_folder: str, filename: str) -> Path:
    report_dir = assert_access_granted_and_scoped(allowed_folder)
    candidate = Path(filename.strip())
    if candidate.name != filename.strip() or candidate.parent != Path("."):
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    target_path = (report_dir / candidate.name).resolve()
    if report_dir not in target_path.parents:
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    return target_path


def resolve_report_output_path(folder: str, title: str, format_name: str, filename: Optional[str]) -> Path:
    report_dir = assert_access_granted_and_scoped(folder)
    extension = f".{format_name}"
    if filename and filename.strip():
        target_name = f"{make_safe_stem(Path(filename.strip()).stem)}{extension}"
    else:
        target_name = f"{datetime.now().strftime('%Y-%m-%d')}-{make_safe_stem(title)}{extension}"
    target_path = (report_dir / target_name).resolve()
    if report_dir not in target_path.parents:
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    return target_path


def ensure_supported_read_extension(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in {".md", ".docx"}:
        raise ValueError("仅支持 .md/.docx 文件。")
    return ext


def ensure_supported_edit_extension(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in {".md", ".docx"}:
        raise ValueError("仅支持编辑 .md/.docx 文件。")
    return ext


def make_backup(path: Path) -> Path:
    backup_path = path.with_name(f"{path.name}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, backup_path)
    return backup_path


def extract_md_headings(lines: List[str]) -> List[tuple[int, int, str]]:
    headings = []
    for idx, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if match:
            headings.append((idx, len(match.group(1)), match.group(2).strip()))
    return headings
