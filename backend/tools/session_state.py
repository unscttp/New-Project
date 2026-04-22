from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .risk_control import set_active_session as set_active_risk_session

UNAUTHORIZED_FILE_ACCESS_TEXT = "未授权文件访问，请先确认目录和权限。"
SCOPED_PATH_DENIED_TEXT = "目标文件不在授权目录内，操作已拒绝。"
ALLOWED_REPORT_EXTENSIONS = {".md", ".docx", ".pdf"}
ERROR_CATEGORY_PERMISSION_DENIED = "permission_denied"
ERROR_CATEGORY_PATH_VIOLATION = "path_violation"
ERROR_CATEGORY_FORMAT_UNSUPPORTED = "format_unsupported"
ERROR_CATEGORY_IO_FAILURE = "io_failure"

ACTIVE_SESSION_ID: str = "default"
SESSION_PERMISSION_STATE: Dict[str, Dict[str, Optional[str] | bool]] = {}
SESSION_AUDIT_LOGS: Dict[str, List[Dict[str, Any]]] = {}


def set_active_session(session_id: str, initial_state: Optional[Dict[str, Any]] = None) -> None:
    global ACTIVE_SESSION_ID
    ACTIVE_SESSION_ID = (session_id or "default").strip() or "default"
    if initial_state is not None:
        SESSION_PERMISSION_STATE[ACTIVE_SESSION_ID] = {
            "file_access_granted": bool(initial_state.get("file_access_granted", False)),
            "allowed_report_folder": initial_state.get("allowed_report_folder"),
        }
    elif ACTIVE_SESSION_ID not in SESSION_PERMISSION_STATE:
        SESSION_PERMISSION_STATE[ACTIVE_SESSION_ID] = {
            "file_access_granted": False,
            "allowed_report_folder": None,
        }
    SESSION_AUDIT_LOGS.setdefault(ACTIVE_SESSION_ID, [])
    set_active_risk_session(ACTIVE_SESSION_ID)


def get_active_permission_state() -> Dict[str, Optional[str] | bool]:
    return SESSION_PERMISSION_STATE.get(
        ACTIVE_SESSION_ID,
        {"file_access_granted": False, "allowed_report_folder": None},
    )


def get_active_audit_entries() -> List[Dict[str, Any]]:
    return list(SESSION_AUDIT_LOGS.get(ACTIVE_SESSION_ID, []))


def record_audit_event(
    operation: str,
    allowed_folder: Optional[str],
    authorization_state: str,
    decision: str,
    target_file: Optional[str] = None,
    error_category: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    event: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "operation": operation,
        "target_file": target_file,
        "allowed_folder": allowed_folder,
        "authorization_state": authorization_state,
        "decision": decision,
    }
    if error_category:
        event["error_category"] = error_category
    if details:
        event["details"] = details
    SESSION_AUDIT_LOGS.setdefault(ACTIVE_SESSION_ID, []).append(event)


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
    if not allowed_folder_text:
        raise ValueError("allowed_folder 不能为空。")

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

    report_dir = state_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    record_audit_event(
        operation="permission_check",
        allowed_folder=str(report_dir),
        authorization_state="authorized",
        decision="allow",
    )
    return report_dir
