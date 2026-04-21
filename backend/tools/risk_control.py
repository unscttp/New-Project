from typing import Dict


RISK_ORDER = {"low": 1, "medium": 2, "high": 3}
SESSION_RISK_LEVELS: Dict[str, str] = {}
ACTIVE_SESSION_ID = "default"


def set_active_session(session_id: str) -> None:
    global ACTIVE_SESSION_ID
    ACTIVE_SESSION_ID = (session_id or "default").strip() or "default"
    SESSION_RISK_LEVELS.setdefault(ACTIVE_SESSION_ID, "high")


def get_active_risk_level() -> str:
    return SESSION_RISK_LEVELS.get(ACTIVE_SESSION_ID, "high")


def set_active_risk_level(level: str) -> str:
    normalized = (level or "").strip().lower()
    if normalized not in RISK_ORDER:
        raise ValueError("risk_level 必须是 low、medium 或 high。")
    SESSION_RISK_LEVELS[ACTIVE_SESSION_ID] = normalized
    return normalized


def assert_tool_access(required_level: str, tool_name: str) -> None:
    active = get_active_risk_level()
    if RISK_ORDER[active] < RISK_ORDER[required_level]:
        raise PermissionError(
            f"当前风险级别为 {active}，无法访问 {required_level} 级工具：{tool_name}。"
        )
