import json


def request_report_folder_access(purpose: str, folder: str) -> str:
    purpose_text = purpose.strip()
    folder_text = folder.strip()
    if not purpose_text:
        raise ValueError("purpose 不能为空。")
    if not folder_text:
        raise ValueError("folder 不能为空。")

    return json.dumps(
        {
            "status": "awaiting_user_confirmation",
            "purpose": purpose_text,
            "folder": folder_text,
            "confirmation_prompt": f"请确认是否授权访问目录：{folder_text}。用途：{purpose_text}",
            "next_action": "请调用 confirm_report_folder_access(granted, folder) 记录结果。",
        },
        ensure_ascii=False,
        indent=2,
    )
