import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .risk_control import assert_tool_access, set_active_risk_level, set_active_session as set_active_risk_session
from .shared.audit import get_active_audit_entries, get_active_permission_state, set_active_session as set_shared_session

BASE_DIR = Path(__file__).resolve().parent


def set_active_session(session_id: str, initial_state: Optional[Dict[str, Any]] = None) -> None:
    set_shared_session(session_id, initial_state)
    set_active_risk_session(session_id)


def _load_tool_registry_config() -> List[Dict[str, Any]]:
    raw = json.loads((BASE_DIR / "tool_registry.json").read_text(encoding="utf-8"))
    tools = raw.get("tools", [])
    if not isinstance(tools, list):
        raise ValueError("tool_registry.json 的 tools 字段必须为列表")
    return tools


def _resolve_object(import_path: str) -> Any:
    module_path, object_name = import_path.split(":", 1)
    return getattr(importlib.import_module(module_path), object_name)


def _build_tool_risk_levels(specs: List[Dict[str, Any]]) -> Dict[str, str]:
    return {str(s["name"]): str(s["risk_level"]).lower() for s in specs}


def _enforce_tool_risk(tool_name: str, risk_levels: Dict[str, str]) -> None:
    assert_tool_access(risk_levels.get(tool_name, "high"), tool_name)


def _build_tool_registry(specs: List[Dict[str, Any]], risk_levels: Dict[str, str]) -> Dict[str, Any]:
    registry: Dict[str, Any] = {}
    for spec in specs:
        name = str(spec["name"])
        callable_obj = _resolve_object(spec["callable_path"])

        def guarded_callable(*args: Any, __name: str = name, __callable=callable_obj, **kwargs: Any) -> Any:
            _enforce_tool_risk(__name, risk_levels)
            return __callable(*args, **kwargs)

        registry[name] = guarded_callable
    return registry


def _build_openai_tools(specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in specs:
        args_model = _resolve_object(s["args_model_path"])
        out.append(
            {
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": args_model.model_json_schema(),
                },
            }
        )
    return out


_TOOL_SPECS = _load_tool_registry_config()
TOOL_RISK_LEVELS = _build_tool_risk_levels(_TOOL_SPECS)
TOOL_REGISTRY = _build_tool_registry(_TOOL_SPECS, TOOL_RISK_LEVELS)
OPENAI_TOOLS: List[Dict[str, Any]] = _build_openai_tools(_TOOL_SPECS)

__all__ = [
    "OPENAI_TOOLS",
    "TOOL_REGISTRY",
    "TOOL_RISK_LEVELS",
    "get_active_audit_entries",
    "get_active_permission_state",
    "set_active_risk_level",
    "set_active_session",
]
