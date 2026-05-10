import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .high_risk.delete_report_file import delete_report_file as delete_report_file_high_risk
from .low_risk.analyze_trend_data import analyze_trend_data as analyze_trend_data_low_risk
from .low_risk.confirm_report_folder_access import confirm_report_folder_access as confirm_report_folder_access_low_risk
from .low_risk.creation import save_report_file as save_report_file_low_risk
from .low_risk.extract_keywords import extract_keywords as extract_keywords_low_risk
from .low_risk.generate_markdown_report import generate_markdown_report as generate_markdown_report_low_risk
from .low_risk.list_report_files import list_report_files as list_report_files_low_risk
from .low_risk.read_report_file import read_report_file as read_report_file_low_risk
from .low_risk.request_report_folder_access import request_report_folder_access as request_report_folder_access_low_risk
from .low_risk.save_report import save_report as save_report_low_risk
from .low_risk.search_internet import search_internet as search_internet_low_risk
from .low_risk.select_tool_risk_level import select_tool_risk_level as select_tool_risk_level_low_risk
from .medium_risk.edit_report import edit_report as edit_report_medium_risk
from .medium_risk.editing import edit_report_file as edit_report_file_medium_risk
from .medium_risk.read_report import read_report as read_report_medium_risk
from .medium_risk.redact_sensitive_text import redact_sensitive_text as redact_sensitive_text_medium_risk
from .risk_control import assert_tool_access, set_active_risk_level, set_active_session as set_active_risk_session
from .shared.audit import get_active_audit_entries, get_active_permission_state, set_active_session as set_shared_session

BASE_DIR = Path(__file__).resolve().parent

def set_active_session(session_id: str, initial_state: Optional[Dict[str, Any]] = None) -> None:
    set_shared_session(session_id, initial_state)
    set_active_risk_session(session_id)

def search_internet(query: str) -> str: return search_internet_low_risk(query)
def analyze_trend_data(data_json: str) -> str: return analyze_trend_data_low_risk(data_json)
def request_report_folder_access(purpose: str, folder: str) -> str: return request_report_folder_access_low_risk(purpose, folder)
def confirm_report_folder_access(granted: bool, folder: str) -> str: return confirm_report_folder_access_low_risk(granted, folder)
def generate_markdown_report(title: str, content: str) -> str: return generate_markdown_report_low_risk(title, content)
def select_tool_risk_level(risk_level: Literal["low", "medium", "high"]) -> str: return select_tool_risk_level_low_risk(risk_level, set_active_risk_level=set_active_risk_level)

def _load_tool_registry_config() -> List[Dict[str, Any]]:
    raw = json.loads((BASE_DIR / "tool_registry.json").read_text(encoding="utf-8")); tools = raw.get("tools", [])
    if not isinstance(tools, list): raise ValueError("tool_registry.json 的 tools 字段必须为列表")
    return tools

def _build_tool_risk_levels(specs: List[Dict[str, Any]]) -> Dict[str, str]:
    return {str(s["name"]): str(s["risk_level"]).lower() for s in specs}

def _resolve_object(import_path: str) -> Any:
    module_path, object_name = import_path.split(":", 1); return getattr(importlib.import_module(module_path), object_name)

def _build_tool_registry(specs: List[Dict[str, Any]]) -> Dict[str, Any]: return {s["name"]: _resolve_object(s["callable_path"]) for s in specs}
def _build_openai_tools(specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out=[]
    for s in specs:
        args_model=_resolve_object(s["args_model_path"])
        out.append({"type":"function","function":{"name":s["name"],"description":s["description"],"parameters":args_model.model_json_schema()}})
    return out

_TOOL_SPECS = _load_tool_registry_config()
TOOL_RISK_LEVELS = _build_tool_risk_levels(_TOOL_SPECS)
def _enforce_tool_risk(tool_name: str) -> None: assert_tool_access(TOOL_RISK_LEVELS.get(tool_name, "high"), tool_name)

def extract_keywords(text: str, top_k: int = 8) -> str: _enforce_tool_risk("extract_keywords"); return extract_keywords_low_risk(text=text, top_k=top_k)
def redact_sensitive_text(content: str) -> str: _enforce_tool_risk("redact_sensitive_text"); return redact_sensitive_text_medium_risk(content=content)
def delete_report_file(allowed_folder: str, filename: str) -> str: _enforce_tool_risk("delete_report_file"); return delete_report_file_high_risk(allowed_folder, filename)
def save_report(title: str, content: str, format: Literal["md", "docx", "pdf"], folder: str, filename: Optional[str] = None) -> str: _enforce_tool_risk("save_report"); return save_report_low_risk(title, content, format, folder, filename)
def save_report_file(allowed_folder: str, filename: str, content: str) -> str: _enforce_tool_risk("save_report_file"); return save_report_file_low_risk(allowed_folder, filename, content)
def read_report_file(allowed_folder: str, filename: str) -> str: _enforce_tool_risk("read_report_file"); return read_report_file_low_risk(allowed_folder, filename)
def edit_report_file(allowed_folder: str, filename: str, content: str) -> str: _enforce_tool_risk("edit_report_file"); return edit_report_file_medium_risk(allowed_folder, filename, content)
def read_report(file_name: str, folder: str) -> str: _enforce_tool_risk("read_report"); return read_report_medium_risk(file_name, folder)
def edit_report(file_name: str, folder: str, instruction: str, mode: Literal["append", "replace_section", "rewrite"]) -> str: _enforce_tool_risk("edit_report"); return edit_report_medium_risk(file_name, folder, instruction, mode)
def list_report_files(allowed_folder: str) -> str: _enforce_tool_risk("list_report_files"); return list_report_files_low_risk(allowed_folder)

TOOL_REGISTRY = _build_tool_registry(_TOOL_SPECS)
OPENAI_TOOLS: List[Dict[str, Any]] = _build_openai_tools(_TOOL_SPECS)
