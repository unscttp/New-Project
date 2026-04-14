import json
from typing import Callable, Literal


def select_tool_risk_level(
    risk_level: Literal["low", "medium", "high"],
    *,
    set_active_risk_level: Callable[[str], str],
) -> str:
    level = set_active_risk_level(risk_level)
    return json.dumps({"risk_level": level}, ensure_ascii=False, indent=2)
