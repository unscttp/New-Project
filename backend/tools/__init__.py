from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .high_risk.delete_report_file import delete_report_file as delete_report_file_high_risk
from .low_risk.analyze_trend_data import analyze_trend_data as analyze_trend_data_low_risk
from .low_risk.confirm_report_folder_access import (
    confirm_report_folder_access as confirm_report_folder_access_low_risk,
)
from .low_risk.creation import save_report_file as save_report_file_low_risk
from .low_risk.extract_keywords import extract_keywords as extract_keywords_low_risk
from .low_risk.generate_markdown_report import (
    generate_markdown_report as generate_markdown_report_low_risk,
)
from .low_risk.list_report_files import list_report_files as list_report_files_low_risk
from .low_risk.read_report_file import read_report_file as read_report_file_low_risk
from .low_risk.request_report_folder_access import (
    request_report_folder_access as request_report_folder_access_low_risk,
)
from .low_risk.save_report import save_report as save_report_low_risk
from .low_risk.search_internet import search_internet as search_internet_low_risk
from .low_risk.select_tool_risk_level import (
    select_tool_risk_level as select_tool_risk_level_low_risk,
)
from .medium_risk.edit_report import edit_report as edit_report_medium_risk
from .medium_risk.editing import edit_report_file as edit_report_file_medium_risk
from .medium_risk.read_report import read_report as read_report_medium_risk
from .medium_risk.redact_sensitive_text import redact_sensitive_text as redact_sensitive_text_medium_risk
from .report_helpers import (
    edit_markdown_content,
    ensure_supported_edit_extension,
    ensure_supported_read_extension,
    extract_numeric_values,
    make_backup,
    parse_replace_instruction,
    resolve_report_output_path,
    resolve_scoped_path,
    safe_report_path,
    sha256_bytes,
    sha256_text,
    write_docx_report,
    write_pdf_report,
)
from .risk_control import assert_tool_access, set_active_risk_level
from .session_state import (
    ACTIVE_SESSION_ID,
    ALLOWED_REPORT_EXTENSIONS,
    ERROR_CATEGORY_PERMISSION_DENIED,
    SCOPED_PATH_DENIED_TEXT,
    SESSION_PERMISSION_STATE,
    UNAUTHORIZED_FILE_ACCESS_TEXT,
    assert_access_granted_and_scoped,
    get_active_audit_entries,
    get_active_permission_state,
    record_audit_event,
    set_active_session,
)
from .tool_metadata import OPENAI_TOOLS, TOOL_RISK_LEVELS

BASE_DIR = Path(__file__).resolve().parent


def search_internet(query: str) -> str:
    return search_internet_low_risk(query)


def analyze_trend_data(data_json: str) -> str:
    return analyze_trend_data_low_risk(data_json, extract_numeric_values=extract_numeric_values)


def request_report_folder_access(purpose: str, folder: str) -> str:
    return request_report_folder_access_low_risk(purpose, folder)


def confirm_report_folder_access(granted: bool, folder: str) -> str:
    return confirm_report_folder_access_low_risk(
        granted,
        folder,
        session_permission_state=SESSION_PERMISSION_STATE,
        active_session_id=ACTIVE_SESSION_ID,
        record_audit_event=record_audit_event,
        unauthorized_file_access_text=UNAUTHORIZED_FILE_ACCESS_TEXT,
        error_category_permission_denied=ERROR_CATEGORY_PERMISSION_DENIED,
    )


def generate_markdown_report(title: str, content: str) -> str:
    return generate_markdown_report_low_risk(
        title,
        content=content,
        get_active_permission_state=get_active_permission_state,
        assert_access_granted_and_scoped=assert_access_granted_and_scoped,
        safe_report_path=safe_report_path,
    )


def _enforce_tool_risk(tool_name: str) -> None:
    required = TOOL_RISK_LEVELS.get(tool_name, "high")
    assert_tool_access(required, tool_name)


def select_tool_risk_level(risk_level: Literal["low", "medium", "high"]) -> str:
    return select_tool_risk_level_low_risk(risk_level, set_active_risk_level=set_active_risk_level)


def extract_keywords(text: str, top_k: int = 8) -> str:
    _enforce_tool_risk("extract_keywords")
    return extract_keywords_low_risk(text=text, top_k=top_k)


def redact_sensitive_text(content: str) -> str:
    _enforce_tool_risk("redact_sensitive_text")
    return redact_sensitive_text_medium_risk(content=content)


def delete_report_file(allowed_folder: str, filename: str) -> str:
    _enforce_tool_risk("delete_report_file")
    return delete_report_file_high_risk(
        allowed_folder=allowed_folder,
        filename=filename,
        resolve_scoped_path=resolve_scoped_path,
        record_audit_event=record_audit_event,
    )


def save_report(
    title: str,
    content: str,
    format: Literal["md", "docx", "pdf"],
    folder: str,
    filename: Optional[str] = None,
) -> str:
    _enforce_tool_risk("save_report")
    return save_report_low_risk(
        title=title,
        content=content,
        format=format,
        folder=folder,
        filename=filename,
        resolve_report_output_path=resolve_report_output_path,
        write_docx_report=write_docx_report,
        write_pdf_report=write_pdf_report,
    )


def save_report_file(allowed_folder: str, filename: str, content: str) -> str:
    _enforce_tool_risk("save_report_file")
    return save_report_file_low_risk(
        allowed_folder,
        filename,
        content,
        resolve_scoped_path=resolve_scoped_path,
        sha256_text=sha256_text,
        record_audit_event=record_audit_event,
    )


def read_report_file(allowed_folder: str, filename: str) -> str:
    _enforce_tool_risk("read_report_file")
    return read_report_file_low_risk(
        allowed_folder=allowed_folder,
        filename=filename,
        resolve_scoped_path=resolve_scoped_path,
        scoped_path_denied_text=SCOPED_PATH_DENIED_TEXT,
    )


def edit_report_file(allowed_folder: str, filename: str, content: str) -> str:
    _enforce_tool_risk("edit_report_file")
    return edit_report_file_medium_risk(
        allowed_folder,
        filename,
        content,
        resolve_scoped_path=resolve_scoped_path,
        scoped_path_denied_text=SCOPED_PATH_DENIED_TEXT,
        sha256_text=sha256_text,
        record_audit_event=record_audit_event,
    )


def read_report(file_name: str, folder: str) -> str:
    _enforce_tool_risk("read_report")
    return read_report_medium_risk(
        file_name=file_name,
        folder=folder,
        resolve_scoped_path=resolve_scoped_path,
        scoped_path_denied_text=SCOPED_PATH_DENIED_TEXT,
        ensure_supported_read_extension=ensure_supported_read_extension,
    )


def edit_report(file_name: str, folder: str, instruction: str, mode: Literal["append", "replace_section", "rewrite"]) -> str:
    _enforce_tool_risk("edit_report")
    return edit_report_medium_risk(
        file_name=file_name,
        folder=folder,
        instruction=instruction,
        mode=mode,
        resolve_scoped_path=resolve_scoped_path,
        scoped_path_denied_text=SCOPED_PATH_DENIED_TEXT,
        ensure_supported_edit_extension=ensure_supported_edit_extension,
        make_backup=make_backup,
        sha256_text=sha256_text,
        sha256_bytes=sha256_bytes,
        edit_markdown_content=edit_markdown_content,
        parse_replace_instruction=parse_replace_instruction,
        record_audit_event=record_audit_event,
    )


def list_report_files(allowed_folder: str) -> str:
    _enforce_tool_risk("list_report_files")
    return list_report_files_low_risk(
        allowed_folder=allowed_folder,
        assert_access_granted_and_scoped=assert_access_granted_and_scoped,
        allowed_report_extensions=ALLOWED_REPORT_EXTENSIONS,
    )


TOOL_REGISTRY: Dict[str, Any] = {
    "search_internet": search_internet,
    "analyze_trend_data": analyze_trend_data,
    "request_report_folder_access": request_report_folder_access,
    "confirm_report_folder_access": confirm_report_folder_access,
    "generate_markdown_report": generate_markdown_report,
    "save_report": save_report,
    "save_report_file": save_report_file,
    "read_report_file": read_report_file,
    "edit_report_file": edit_report_file,
    "read_report": read_report,
    "edit_report": edit_report,
    "list_report_files": list_report_files,
    "select_tool_risk_level": select_tool_risk_level,
    "extract_keywords": extract_keywords,
    "redact_sensitive_text": redact_sensitive_text,
    "delete_report_file": delete_report_file,
}
