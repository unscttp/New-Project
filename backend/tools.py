import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REPORTS_DIR = (BASE_DIR / "generated_reports").resolve()
DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_REPORT_EXTENSIONS = {".md", ".docx", ".pdf"}


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
    allowed_folder: str = Field(
        default=str(DEFAULT_REPORTS_DIR),
        description="当前授权可访问的目录路径。",
    )
    access_granted: bool = Field(default=False, description="当前会话是否已获得目录访问授权。")


class SaveReportArgs(BaseModel):
    filename: str = Field(..., description="报告文件名（仅文件名，不支持路径）。")
    content: str = Field(..., description="报告正文内容。")
    allowed_folder: str = Field(..., description="当前授权可访问的目录路径。")
    access_granted: bool = Field(default=False, description="当前会话是否已获得目录访问授权。")


class ReadReportArgs(BaseModel):
    filename: str = Field(..., description="要读取的报告文件名（仅文件名，不支持路径）。")
    allowed_folder: str = Field(..., description="当前授权可访问的目录路径。")
    access_granted: bool = Field(default=False, description="当前会话是否已获得目录访问授权。")


class EditReportArgs(BaseModel):
    filename: str = Field(..., description="要编辑的报告文件名（仅文件名，不支持路径）。")
    content: str = Field(..., description="新的完整文件内容。")
    allowed_folder: str = Field(..., description="当前授权可访问的目录路径。")
    access_granted: bool = Field(default=False, description="当前会话是否已获得目录访问授权。")


class ListReportsArgs(BaseModel):
    allowed_folder: str = Field(..., description="当前授权可访问的目录路径。")
    access_granted: bool = Field(default=False, description="当前会话是否已获得目录访问授权。")


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


def _sanitize_filename(filename: str) -> str:
    normalized = filename.strip()
    if not normalized:
        raise ValueError("filename 不能为空。")

    candidate = Path(normalized)
    if candidate.name != normalized or normalized in {".", ".."}:
        raise ValueError("仅允许传入文件名，不允许路径。")

    return normalized


def resolve_scoped_path(allowed_folder: str, filename: str) -> Path:
    safe_filename = _sanitize_filename(filename)
    scoped_dir = Path(allowed_folder).expanduser().resolve()
    target_path = (scoped_dir / safe_filename).resolve()

    if target_path.parent != scoped_dir:
        raise ValueError("目标文件不在授权目录内，操作已拒绝。")

    return target_path


def assert_access_granted_and_scoped(
    allowed_folder: str,
    filename: str,
    *,
    access_granted: bool,
    require_exists: bool = False,
) -> Path:
    if not access_granted:
        raise PermissionError("未获得目录访问授权，操作已拒绝。")

    target_path = resolve_scoped_path(allowed_folder, filename)
    if require_exists and not target_path.exists():
        raise FileNotFoundError(f"目标文件不存在：{target_path.name}")

    return target_path


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


def generate_markdown_report(
    title: str,
    content: str,
    allowed_folder: str = str(DEFAULT_REPORTS_DIR),
    access_granted: bool = False,
) -> str:
    """在授权目录中生成 Markdown 报告，并做路径安全校验。"""
    if not title.strip():
        raise ValueError("title 不能为空。")

    safe_title = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", title).strip("-_")
    safe_title = safe_title or "untitled-report"
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{safe_title}.md"

    report_path = assert_access_granted_and_scoped(
        allowed_folder,
        filename,
        access_granted=access_granted,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    markdown = f"# {title.strip()}\n\n{content.strip()}\n"
    report_path.write_text(markdown, encoding="utf-8")
    return f"报告已生成：{report_path.name}"


def save_report(filename: str, content: str, allowed_folder: str, access_granted: bool = False) -> str:
    report_path = assert_access_granted_and_scoped(
        allowed_folder,
        filename,
        access_granted=access_granted,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    return f"报告已保存：{report_path.name}"


def read_report(filename: str, allowed_folder: str, access_granted: bool = False) -> str:
    report_path = assert_access_granted_and_scoped(
        allowed_folder,
        filename,
        access_granted=access_granted,
        require_exists=True,
    )
    return report_path.read_text(encoding="utf-8")


def edit_report(filename: str, content: str, allowed_folder: str, access_granted: bool = False) -> str:
    report_path = assert_access_granted_and_scoped(
        allowed_folder,
        filename,
        access_granted=access_granted,
        require_exists=True,
    )
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    return f"报告已更新：{report_path.name}"


def list_reports(allowed_folder: str, access_granted: bool = False) -> str:
    if not access_granted:
        raise PermissionError("未获得目录访问授权，操作已拒绝。")

    scoped_dir = Path(allowed_folder).expanduser().resolve()
    if not scoped_dir.exists() or not scoped_dir.is_dir():
        raise FileNotFoundError("授权目录不存在或不可访问。")

    file_names = sorted(
        item.name
        for item in scoped_dir.iterdir()
        if item.is_file() and item.suffix.lower() in ALLOWED_REPORT_EXTENSIONS
    )
    if not file_names:
        return "授权目录内暂无可用报告文件。"

    return "\n".join(file_names)


TOOL_REGISTRY = {
    "search_internet": search_internet,
    "analyze_trend_data": analyze_trend_data,
    "generate_markdown_report": generate_markdown_report,
    "save_report": save_report,
    "read_report": read_report,
    "edit_report": edit_report,
    "list_reports": list_reports,
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
            "name": "generate_markdown_report",
            "description": "把给定标题和内容保存为 Markdown 报告到授权目录。",
            "parameters": GenerateMarkdownReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_report",
            "description": "将内容保存为报告文件。仅允许在授权目录中按文件名写入。",
            "parameters": SaveReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_report",
            "description": "读取授权目录内的报告文件内容。仅允许传入文件名。",
            "parameters": ReadReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_report",
            "description": "编辑授权目录内的报告文件。仅允许传入文件名。",
            "parameters": EditReportArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reports",
            "description": "列出授权目录内的报告文件（仅 .md/.docx/.pdf）。",
            "parameters": ListReportsArgs.model_json_schema(),
        },
    },
]
