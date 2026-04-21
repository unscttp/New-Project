import json
from typing import Any, Callable, Dict


def confirm_report_folder_access(
    granted: bool,
    folder: str,
    *,
    session_permission_state: Dict[str, Dict[str, Any]],
    active_session_id: str,
    record_audit_event: Callable[..., None],
    unauthorized_file_access_text: str,
    error_category_permission_denied: str,
) -> str:
    folder_text = folder.strip()
    if not folder_text:
        raise ValueError("folder 不能为空。")

    session_permission_state[active_session_id] = {
        "file_access_granted": bool(granted),
        "allowed_report_folder": folder_text if granted else None,
    }
    record_audit_event(
        operation="confirm_report_folder_access",
        allowed_folder=folder_text,
        authorization_state="authorized" if granted else "unauthorized",
        decision="allow" if granted else "deny",
        error_category=None if granted else error_category_permission_denied,
    )
    if granted:
        return json.dumps(
            {
                "status": "granted",
                "file_access_granted": True,
                "allowed_report_folder": folder_text,
            },
            ensure_ascii=False,
            indent=2,
        )

    return json.dumps(
        {
            "status": "denied",
            "file_access_granted": False,
            "allowed_report_folder": None,
            "message": unauthorized_file_access_text,
        },
        ensure_ascii=False,
        indent=2,
    )
