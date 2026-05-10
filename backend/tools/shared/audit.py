import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

ACTIVE_SESSION_ID: str = "default"
SESSION_PERMISSION_STATE: Dict[str, Dict[str, Optional[str] | bool]] = {}
SESSION_AUDIT_LOGS: Dict[str, List[Dict[str, Any]]] = {}
ERROR_CATEGORY_PERMISSION_DENIED = "permission_denied"
ERROR_CATEGORY_PATH_VIOLATION = "path_violation"
ERROR_CATEGORY_FORMAT_UNSUPPORTED = "format_unsupported"
ERROR_CATEGORY_IO_FAILURE = "io_failure"


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


def get_active_permission_state() -> Dict[str, Optional[str] | bool]:
    return SESSION_PERMISSION_STATE.get(
        ACTIVE_SESSION_ID,
        {"file_access_granted": False, "allowed_report_folder": None},
    )


def get_active_audit_entries() -> List[Dict[str, Any]]:
    return list(SESSION_AUDIT_LOGS.get(ACTIVE_SESSION_ID, []))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
