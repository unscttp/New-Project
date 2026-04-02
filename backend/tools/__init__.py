import json
import re
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .low_risk.creation import save_report_file as save_report_file_low_risk
from .medium_risk.editing import edit_report_file as edit_report_file_medium_risk
from .risk_control import (
    assert_tool_access,
    set_active_risk_level,
    set_active_session as set_active_risk_session,
)


BASE_DIR = Path(__file__).resolve().parent
UNAUTHORIZED_FILE_ACCESS_TEXT = "未授权文件访问，请先确认目录和权限。"
SCOPED_PATH_DENIED_TEXT = "目标文件不在授权目录内，操作已拒绝。"
ALLOWED_REPORT_EXTENSIONS = {".md", ".docx", ".pdf"}
ACTIVE_SESSION_ID: str = "default"
SESSION_PERMISSION_STATE: Dict[str, Dict[str, Optional[str] | bool]] = {}
SESSION_AUDIT_LOGS: Dict[str, List[Dict[str, Any]]] = {}
ERROR_CATEGORY_PERMISSION_DENIED = "permission_denied"
ERROR_CATEGORY_PATH_VIOLATION = "path_violation"
ERROR_CATEGORY_FORMAT_UNSUPPORTED = "format_unsupported"
ERROR_CATEGORY_IO_FAILURE = "io_failure"


class SearchInternetArgs(BaseModel):
    query: str = Field(..., description="要搜索的互联网关键词或问题。")


class AnalyzeTrendDataArgs(BaseModel):
    data_json: str = Field(
        ...,
        description="JSON 字符串，支持数字数组或包含数值字段的对象数组。",
    )


class GenerateMarkdownReportArgs(BaseModel):
    title: str = Field(..., description="Markdown 报告标题。")
    content: str = Field(..., description="Markdown 报告正文内容。")


class RequestReportFolderAccessArgs(BaseModel):
    purpose: str = Field(..., description="申请访问该目录的用途说明。")
    folder: str = Field(..., description="希望访问并保存报告的目录绝对路径。")


class ConfirmReportFolderAccessArgs(BaseModel):
    granted: bool = Field(..., description="用户是否同意授权。")
    folder: str = Field(..., description="用户确认授权的目录绝对路径。")


class SaveReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")
    content: str = Field(..., description="要写入文件的文本内容。")


class ReadReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")


class EditReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")
    content: str = Field(..., description="编辑后完整内容（覆盖写入）。")


class ReadReportArgs(BaseModel):
    file_name: str = Field(..., description="仅文件名，例如 summary.md。")
    folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")


class EditReportArgs(BaseModel):
    file_name: str = Field(..., description="仅文件名，例如 summary.md。")
    folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    instruction: str = Field(
        ...,
        description="编辑指令文本。replace_section 模式建议使用“section: 节标题\\n---\\n新内容”。",
    )
    mode: Literal["append", "replace_section", "rewrite"] = Field(
        ...,
        description="编辑模式：append、replace_section、rewrite。",
    )


class ListReportFilesArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")




class SelectToolRiskLevelArgs(BaseModel):
    risk_level: Literal["low", "medium", "high"] = Field(
        ...,
        description="工具风险级别：low、medium、high。",
    )

class SaveReportArgs(BaseModel):
    title: str = Field(..., description="报告标题。")
    content: str = Field(..., description="报告正文，可为 markdown 或纯文本。")
    format: Literal["md", "docx", "pdf"] = Field(..., description="导出格式：md、docx、pdf。")
    folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: Optional[str] = Field(
        default=None,
        description="可选文件名（可不含后缀）。为空时自动生成日期+标题文件名。",
    )


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
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


def _extract_numeric_values(payload: Any) -> List[float]:
    if isinstance(payload, list):
        if all(isinstance(item, (int, float)) for item in payload):
            return [float(item) for item in payload]

        values: List[float] = []
        for item in payload:
            if isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, (int, float)):
                        values.append(float(value))
            elif isinstance(item, (int, float)):
                values.append(float(item))
        return values

    if isinstance(payload, dict):
        return [float(value) for value in payload.values() if isinstance(value, (int, float))]

    return []


def search_internet(query: str) -> str:
    """使用 DuckDuckGo 执行轻量搜索并返回文本摘要。"""
    query = query.strip()
    if not query:
        raise ValueError("query 不能为空。")

    summaries: List[str] = []
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        for index, item in enumerate(results, start=1):
            title = (item.get("title") or "").strip()
            body = (item.get("body") or "").strip()
            href = (item.get("href") or "").strip()
            summaries.append(f"{index}. {title}\n摘要: {body}\n链接: {href}")

    if not summaries:
        return f"未找到与“{query}”相关的搜索结果。"

    return "\n\n".join(summaries)


def analyze_trend_data(data_json: str) -> str:
    """对 JSON 中的数值做基础统计。"""
    try:
        payload = json.loads(data_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"data_json 不是合法 JSON: {exc}") from exc

    values = _extract_numeric_values(payload)
    if not values:
        raise ValueError("未从 data_json 中提取到可分析的数值。")

    series = pd.Series(values, dtype="float64")
    result = {
        "count": int(series.count()),
        "mean": round(float(series.mean()), 4),
        "max": round(float(series.max()), 4),
        "min": round(float(series.min()), 4),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _safe_report_path(title: str, report_dir: Path) -> Path:
    safe_title = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", title).strip("-_")
    safe_title = safe_title or "untitled-report"
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{safe_title}.md"

    target_path = (report_dir / filename).resolve()
    if report_dir not in target_path.parents and target_path != report_dir:
        raise ValueError("非法文件路径，已阻止目录穿越。")

    return target_path


def _make_safe_stem(stem: str) -> str:
    safe_stem = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", stem).strip("-_")
    return safe_stem or "untitled-report"


def _resolve_report_output_path(folder: str, title: str, format_name: str, filename: Optional[str]) -> Path:
    report_dir = assert_access_granted_and_scoped(folder)
    extension = f".{format_name}"

    if filename and filename.strip():
        raw_name = filename.strip()
        raw_path = Path(raw_name)
        if raw_path.name != raw_name or raw_path.parent != Path("."):
            raise PermissionError(SCOPED_PATH_DENIED_TEXT)
        stem = _make_safe_stem(raw_path.stem)
        target_name = f"{stem}{extension}"
    else:
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        target_name = f"{date_prefix}-{_make_safe_stem(title)}{extension}"

    target_path = (report_dir / target_name).resolve()
    if report_dir not in target_path.parents:
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    return target_path


def _iter_content_lines(content: str) -> List[str]:
    cleaned = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return cleaned.split("\n") if cleaned else []


def _write_docx_report(path: Path, title: str, content: str) -> None:
    doc = Document()
    doc.add_heading(title.strip(), level=1)
    for line in _iter_content_lines(content):
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph("")
            continue
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip() or " "
            doc.add_heading(heading_text, level=2)
        else:
            doc.add_paragraph(stripped)
    doc.save(path)


def _write_pdf_report(path: Path, title: str, content: str) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    margin_x = 50
    y = height - 60

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin_x, y, title.strip() or "Untitled Report")
    y -= 30

    pdf.setFont("Helvetica", 11)
    for line in _iter_content_lines(content):
        stripped = line.strip()
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 60
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip() or " "
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(margin_x, y, text)
            pdf.setFont("Helvetica", 11)
        else:
            pdf.drawString(margin_x, y, stripped)
        y -= 18

    pdf.save()


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


def resolve_scoped_path(allowed_folder: str, filename: str) -> Path:
    report_dir = assert_access_granted_and_scoped(allowed_folder)
    filename_text = filename.strip()
    if not filename_text:
        raise ValueError("filename 不能为空。")

    candidate = Path(filename_text)
    if candidate.name != filename_text or candidate.parent != Path("."):
        record_audit_event(
            operation="path_resolution",
            target_file=filename_text,
            allowed_folder=allowed_folder.strip(),
            authorization_state="authorized",
            decision="deny",
            error_category=ERROR_CATEGORY_PATH_VIOLATION,
            details={"reason": "invalid_filename"},
        )
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)

    target_path = (report_dir / candidate.name).resolve()
    if report_dir not in target_path.parents:
        record_audit_event(
            operation="path_resolution",
            target_file=filename_text,
            allowed_folder=str(report_dir),
            authorization_state="authorized",
            decision="deny",
            error_category=ERROR_CATEGORY_PATH_VIOLATION,
            details={"reason": "path_out_of_scope"},
        )
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    record_audit_event(
        operation="path_resolution",
        target_file=target_path.name,
        allowed_folder=str(report_dir),
        authorization_state="authorized",
        decision="allow",
    )
    return target_path


def _ensure_supported_read_extension(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in {".md", ".docx"}:
        if ext == ".pdf":
            record_audit_event(
                operation="read_report",
                target_file=path.name,
                allowed_folder=str(path.parent),
                authorization_state="authorized",
                decision="deny",
                error_category=ERROR_CATEGORY_FORMAT_UNSUPPORTED,
            )
            raise ValueError("MVP 暂不支持读取 PDF 正文；仅支持 .md/.docx。")
        record_audit_event(
            operation="read_report",
            target_file=path.name,
            allowed_folder=str(path.parent),
            authorization_state="authorized",
            decision="deny",
            error_category=ERROR_CATEGORY_FORMAT_UNSUPPORTED,
        )
        raise ValueError("仅支持 .md/.docx 文件。")
    return ext


def _ensure_supported_edit_extension(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        record_audit_event(
            operation="edit_report",
            target_file=path.name,
            allowed_folder=str(path.parent),
            authorization_state="authorized",
            decision="deny",
            error_category=ERROR_CATEGORY_FORMAT_UNSUPPORTED,
        )
        raise ValueError("MVP 暂不支持编辑 PDF；请改用 .md/.docx。")
    if ext not in {".md", ".docx"}:
        record_audit_event(
            operation="edit_report",
            target_file=path.name,
            allowed_folder=str(path.parent),
            authorization_state="authorized",
            decision="deny",
            error_category=ERROR_CATEGORY_FORMAT_UNSUPPORTED,
        )
        raise ValueError("仅支持编辑 .md/.docx 文件。")
    return ext


def _make_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def _parse_replace_instruction(instruction: str) -> tuple[str, str]:
    text = instruction.strip()
    if "\n---\n" in text:
        head, body = text.split("\n---\n", 1)
    else:
        lines = text.splitlines()
        if len(lines) < 2:
            raise ValueError("replace_section 模式需要 section 标题和新内容。")
        head, body = lines[0], "\n".join(lines[1:])

    section = re.sub(r"^section\s*:\s*", "", head.strip(), flags=re.IGNORECASE).strip().lstrip("#").strip()
    if not section:
        raise ValueError("replace_section 模式缺少 section 标题。")
    return section, body.strip()


def _extract_md_headings(lines: List[str]) -> List[tuple[int, int, str]]:
    headings: List[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append((idx, level, title))
    return headings


def _edit_markdown_content(original: str, instruction: str, mode: str) -> tuple[str, List[str], int]:
    normalized = original.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    changed_sections: List[str] = []

    if mode == "append":
        append_text = instruction.strip()
        if not append_text:
            raise ValueError("append 模式下 instruction 不能为空。")
        merged = normalized.rstrip("\n")
        if merged:
            merged = f"{merged}\n\n{append_text}\n"
        else:
            merged = f"{append_text}\n"
        return merged, ["__appended__"], len(append_text.splitlines())

    if mode == "rewrite":
        rewritten = instruction.strip()
        if not rewritten:
            raise ValueError("rewrite 模式下 instruction 不能为空。")
        return f"{rewritten}\n", ["__all__"], len(rewritten.splitlines())

    section_name, replacement = _parse_replace_instruction(instruction)
    headings = _extract_md_headings(lines)
    target_index = None
    target_level = None
    for idx, level, title in headings:
        if title.lower() == section_name.lower():
            target_index = idx
            target_level = level
            break
    if target_index is None or target_level is None:
        raise ValueError(f"未找到 Markdown 节：{section_name}")

    end_index = len(lines)
    for idx, level, _ in headings:
        if idx > target_index and level <= target_level:
            end_index = idx
            break

    heading_line = lines[target_index]
    replacement_block = [heading_line]
    replacement_lines = replacement.splitlines()
    if replacement_lines:
        replacement_block.extend(replacement_lines)
    new_lines = lines[:target_index] + replacement_block + lines[end_index:]
    changed_sections.append(section_name)
    return "\n".join(new_lines).rstrip("\n") + "\n", changed_sections, len(replacement_lines)


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


def confirm_report_folder_access(granted: bool, folder: str) -> str:
    folder_text = folder.strip()
    if not folder_text:
        raise ValueError("folder 不能为空。")

    SESSION_PERMISSION_STATE[ACTIVE_SESSION_ID] = {
        "file_access_granted": bool(granted),
        "allowed_report_folder": folder_text if granted else None,
    }
    record_audit_event(
        operation="confirm_report_folder_access",
        allowed_folder=folder_text,
        authorization_state="authorized" if granted else "unauthorized",
        decision="allow" if granted else "deny",
        error_category=None if granted else ERROR_CATEGORY_PERMISSION_DENIED,
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
            "message": UNAUTHORIZED_FILE_ACCESS_TEXT,
        },
        ensure_ascii=False,
        indent=2,
    )


def generate_markdown_report(title: str, content: str) -> str:
    """在授权目录中生成 Markdown 报告，并做路径安全校验。"""
    if not title.strip():
        raise ValueError("title 不能为空。")

    state = get_active_permission_state()
    folder = str(state.get("allowed_report_folder") or "")
    report_dir = assert_access_granted_and_scoped(folder)
    report_path = _safe_report_path(title, report_dir)
    markdown = f"# {title.strip()}\n\n{content.strip()}\n"
    report_path.write_text(markdown, encoding="utf-8")
    return f"报告已生成：{report_path}"



TOOL_RISK_LEVELS: Dict[str, str] = {
    "search_internet": "low",
    "analyze_trend_data": "low",
    "request_report_folder_access": "low",
    "confirm_report_folder_access": "low",
    "generate_markdown_report": "low",
    "save_report": "low",
    "save_report_file": "low",
    "read_report_file": "low",
    "edit_report_file": "medium",
    "read_report": "medium",
    "edit_report": "medium",
    "list_report_files": "low",
    "select_tool_risk_level": "low",
}


def _enforce_tool_risk(tool_name: str) -> None:
    required = TOOL_RISK_LEVELS.get(tool_name, "high")
    assert_tool_access(required, tool_name)


def select_tool_risk_level(risk_level: Literal["low", "medium", "high"]) -> str:
    level = set_active_risk_level(risk_level)
    return json.dumps({"risk_level": level}, ensure_ascii=False, indent=2)

def save_report(
    title: str,
    content: str,
    format: Literal["md", "docx", "pdf"],
    folder: str,
    filename: Optional[str] = None,
) -> str:
    _enforce_tool_risk("save_report")
    title_text = title.strip()
    if not title_text:
        raise ValueError("title 不能为空。")

    content_text = content.strip()
    if not content_text:
        raise ValueError("content 不能为空。")

    target_path = _resolve_report_output_path(folder, title_text, format, filename)
    if format == "md":
        markdown = f"# {title_text}\n\n{content_text}\n"
        target_path.write_text(markdown, encoding="utf-8")
    elif format == "docx":
        _write_docx_report(target_path, title_text, content_text)
    elif format == "pdf":
        _write_pdf_report(target_path, title_text, content_text)
    else:
        raise ValueError("不支持的 format，必须是 md/docx/pdf。")

    return f"报告已导出：{target_path}"


def save_report_file(allowed_folder: str, filename: str, content: str) -> str:
    _enforce_tool_risk("save_report_file")
    return save_report_file_low_risk(
        allowed_folder,
        filename,
        content,
        resolve_scoped_path=resolve_scoped_path,
        sha256_text=_sha256_text,
        record_audit_event=record_audit_event,
    )


def read_report_file(allowed_folder: str, filename: str) -> str:
    _enforce_tool_risk("read_report_file")
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    return target_path.read_text(encoding="utf-8")


def edit_report_file(allowed_folder: str, filename: str, content: str) -> str:
    _enforce_tool_risk("edit_report_file")
    return edit_report_file_medium_risk(
        allowed_folder,
        filename,
        content,
        resolve_scoped_path=resolve_scoped_path,
        scoped_path_denied_text=SCOPED_PATH_DENIED_TEXT,
        sha256_text=_sha256_text,
        record_audit_event=record_audit_event,
    )


def read_report(file_name: str, folder: str) -> str:
    _enforce_tool_risk("read_report")
    target_path = resolve_scoped_path(folder, file_name)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)

    ext = _ensure_supported_read_extension(target_path)
    if ext == ".md":
        content = target_path.read_text(encoding="utf-8")
        return json.dumps(
            {
                "file_name": target_path.name,
                "format": "md",
                "line_count": len(content.splitlines()),
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )

    doc = Document(target_path)
    paragraphs = [p.text for p in doc.paragraphs]
    return json.dumps(
        {
            "file_name": target_path.name,
            "format": "docx",
            "paragraph_count": len(paragraphs),
            "content": "\n".join(paragraphs),
        },
        ensure_ascii=False,
        indent=2,
    )


def edit_report(file_name: str, folder: str, instruction: str, mode: Literal["append", "replace_section", "rewrite"]) -> str:
    _enforce_tool_risk("edit_report")
    target_path = resolve_scoped_path(folder, file_name)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)

    ext = _ensure_supported_edit_extension(target_path)
    backup_path = _make_backup(target_path)

    if ext == ".md":
        original = target_path.read_text(encoding="utf-8")
        before_hash = _sha256_text(original)
        new_content, sections, touched_lines = _edit_markdown_content(original, instruction, mode)
        target_path.write_text(new_content, encoding="utf-8")
        after_hash = _sha256_text(new_content)
        summary = {
            "file_name": target_path.name,
            "format": "md",
            "mode": mode,
            "changed_sections": sections,
            "line_count_before": len(original.splitlines()),
            "line_count_after": len(new_content.splitlines()),
            "touched_line_count": touched_lines,
            "backup_path": str(backup_path),
            "checksum_before": before_hash,
            "checksum_after": after_hash,
        }
        record_audit_event(
            operation="edit_report",
            target_file=target_path.name,
            allowed_folder=str(target_path.parent),
            authorization_state="authorized",
            decision="allow",
            details={
                "mode": mode,
                "changed_sections": sections,
                "checksum_before": before_hash,
                "checksum_after": after_hash,
            },
        )
        return json.dumps(summary, ensure_ascii=False, indent=2)

    doc = Document(target_path)
    before_hash = _sha256_bytes(target_path.read_bytes())
    changed_sections: List[str] = []
    paragraph_count_before = len(doc.paragraphs)
    touched_paragraphs = 0

    if mode == "append":
        append_text = instruction.strip()
        if not append_text:
            raise ValueError("append 模式下 instruction 不能为空。")
        for line in append_text.splitlines():
            doc.add_paragraph(line)
            touched_paragraphs += 1
        changed_sections = ["__appended__"]
    elif mode == "rewrite":
        for _ in range(len(doc.paragraphs)):
            p = doc.paragraphs[0]._element
            p.getparent().remove(p)
        for line in instruction.strip().splitlines():
            doc.add_paragraph(line)
            touched_paragraphs += 1
        changed_sections = ["__all__"]
    else:
        section_name, replacement = _parse_replace_instruction(instruction)
        replacement_lines = replacement.splitlines()
        start_idx = None
        for idx, paragraph in enumerate(doc.paragraphs):
            if paragraph.text.strip().lower() == section_name.lower():
                start_idx = idx
                break
        if start_idx is None:
            raise ValueError(f"未找到 DOCX 段落标题：{section_name}")
        end_idx = len(doc.paragraphs)
        for idx in range(start_idx + 1, len(doc.paragraphs)):
            if doc.paragraphs[idx].style and str(doc.paragraphs[idx].style.name).lower().startswith("heading"):
                end_idx = idx
                break
        anchor = doc.paragraphs[start_idx]._element
        for _ in range(end_idx - start_idx - 1):
            nxt = anchor.getnext()
            if nxt is not None:
                nxt.getparent().remove(nxt)
                touched_paragraphs += 1
        for line in replacement_lines:
            new_para = doc.add_paragraph(line)
            anchor.addnext(new_para._element)
            anchor = new_para._element
            touched_paragraphs += 1
        changed_sections = [section_name]

    doc.save(target_path)
    after_hash = _sha256_bytes(target_path.read_bytes())
    summary = {
        "file_name": target_path.name,
        "format": "docx",
        "mode": mode,
        "changed_sections": changed_sections,
        "paragraph_count_before": paragraph_count_before,
        "paragraph_count_after": len(Document(target_path).paragraphs),
        "touched_paragraph_count": touched_paragraphs,
        "backup_path": str(backup_path),
        "checksum_before": before_hash,
        "checksum_after": after_hash,
    }
    record_audit_event(
        operation="edit_report",
        target_file=target_path.name,
        allowed_folder=str(target_path.parent),
        authorization_state="authorized",
        decision="allow",
        details={
            "mode": mode,
            "changed_sections": changed_sections,
            "checksum_before": before_hash,
            "checksum_after": after_hash,
        },
    )
    return json.dumps(summary, ensure_ascii=False, indent=2)


def list_report_files(allowed_folder: str) -> str:
    _enforce_tool_risk("list_report_files")
    report_dir = assert_access_granted_and_scoped(allowed_folder)
    files = sorted(
        [
            item.name
            for item in report_dir.iterdir()
            if item.is_file() and item.suffix.lower() in ALLOWED_REPORT_EXTENSIONS
        ]
    )
    return json.dumps(
        {"allowed_folder": str(report_dir), "files": files},
        ensure_ascii=False,
        indent=2,
    )


TOOL_REGISTRY = {
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
}


OPENAI_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_internet",
            "description": "搜索互联网公开信息，返回轻量级文本摘要列表。",
            "parameters": SearchInternetArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_trend_data",
            "description": "对 JSON 数值数据做基础统计分析，返回均值、最大值、最小值等结果。",
            "parameters": AnalyzeTrendDataArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_report_folder_access",
            "description": "申请访问报告目录，仅记录授权意图并返回确认提示，不执行任何文件写入。",
            "parameters": RequestReportFolderAccessArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_report_folder_access",
            "description": "记录用户对报告目录访问授权的确认结果，持久化到当前会话状态。",
            "parameters": ConfirmReportFolderAccessArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_markdown_report",
            "description": "把给定标题和内容保存为 Markdown 报告到已授权目录。",
            "parameters": GenerateMarkdownReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_report",
            "description": "在已授权目录导出报告为 md/docx/pdf；调用前必须完成 request_report_folder_access + confirm_report_folder_access，并将 folder 设为已授权目录。",
            "parameters": SaveReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_report_file",
            "description": "在授权目录内按文件名保存报告内容，拒绝任意路径输入。",
            "parameters": SaveReportFileArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_report_file",
            "description": "在授权目录内按文件名读取报告内容，拒绝任意路径输入。",
            "parameters": ReadReportFileArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_report_file",
            "description": "在授权目录内按文件名覆盖编辑报告内容，拒绝任意路径输入。",
            "parameters": EditReportFileArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_report",
            "description": "读取授权目录中的 .md/.docx 报告内容（MVP 不支持 PDF 正文读取）。",
            "parameters": ReadReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_report",
            "description": "编辑授权目录中的 .md/.docx 报告，支持 append/replace_section/rewrite，并自动创建同目录备份。",
            "parameters": EditReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_report_files",
            "description": "仅列出授权目录内 .md/.docx/.pdf 文件名。",
            "parameters": ListReportFilesArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "select_tool_risk_level",
            "description": "设置当前会话的工具风险级别（low/medium/high），用于限制可调用工具范围。",
            "parameters": SelectToolRiskLevelArgs.model_json_schema(),
        },
    }

]
