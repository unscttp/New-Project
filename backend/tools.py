import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = (BASE_DIR / "generated_reports").resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


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


def _safe_report_path(title: str) -> Path:
    safe_title = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", title).strip("-_")
    safe_title = safe_title or "untitled-report"
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{safe_title}.md"

    target_path = (REPORTS_DIR / filename).resolve()
    if REPORTS_DIR not in target_path.parents and target_path != REPORTS_DIR:
        raise ValueError("非法文件路径，已阻止目录穿越。")

    return target_path


def generate_markdown_report(title: str, content: str) -> str:
    """在固定目录中生成 Markdown 报告，并做路径安全校验。"""
    if not title.strip():
        raise ValueError("title 不能为空。")

    report_path = _safe_report_path(title)
    markdown = f"# {title.strip()}\n\n{content.strip()}\n"
    report_path.write_text(markdown, encoding="utf-8")
    return f"报告已生成：{report_path}"


TOOL_REGISTRY = {
    "search_internet": search_internet,
    "analyze_trend_data": analyze_trend_data,
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
            "name": "generate_markdown_report",
            "description": "把给定标题和内容保存为 Markdown 报告到固定目录。",
            "parameters": GenerateMarkdownReportArgs.model_json_schema(),
        },
    },
]
