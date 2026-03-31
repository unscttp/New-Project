import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = (BASE_DIR / "generated_reports").resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
UNAUTHORIZED_FILE_ACCESS_TEXT = "未授权文件访问，请先确认目录和权限。"
ACTIVE_SESSION_ID: str = "default"
SESSION_PERMISSION_STATE: Dict[str, Dict[str, Optional[str] | bool]] = {}


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


def get_active_permission_state() -> Dict[str, Optional[str] | bool]:
    return SESSION_PERMISSION_STATE.get(
        ACTIVE_SESSION_ID,
        {"file_access_granted": False, "allowed_report_folder": None},
    )


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


def _require_report_folder_access() -> Path:
    state = get_active_permission_state()
    granted = bool(state.get("file_access_granted"))
    folder = state.get("allowed_report_folder")
    if not granted or not folder or not str(folder).strip():
        raise PermissionError(UNAUTHORIZED_FILE_ACCESS_TEXT)

    report_dir = Path(str(folder)).expanduser().resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


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

    report_dir = _require_report_folder_access()
    report_path = _safe_report_path(title, report_dir)
    markdown = f"# {title.strip()}\n\n{content.strip()}\n"
    report_path.write_text(markdown, encoding="utf-8")
    return f"报告已生成：{report_path}"


TOOL_REGISTRY = {
    "search_internet": search_internet,
    "analyze_trend_data": analyze_trend_data,
    "request_report_folder_access": request_report_folder_access,
    "confirm_report_folder_access": confirm_report_folder_access,
    "generate_markdown_report": generate_markdown_report,
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
]
