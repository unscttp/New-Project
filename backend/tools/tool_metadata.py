from __future__ import annotations

from typing import Any, Dict, List

from .tool_schemas import (
    AnalyzeTrendDataArgs,
    ConfirmReportFolderAccessArgs,
    DeleteReportFileArgs,
    EditReportArgs,
    EditReportFileArgs,
    ExtractKeywordsArgs,
    GenerateMarkdownReportArgs,
    ListReportFilesArgs,
    ReadReportArgs,
    ReadReportFileArgs,
    RedactSensitiveTextArgs,
    RequestReportFolderAccessArgs,
    SaveReportArgs,
    SaveReportFileArgs,
    SearchInternetArgs,
    SelectToolRiskLevelArgs,
)

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
    "extract_keywords": "low",
    "redact_sensitive_text": "medium",
    "delete_report_file": "high",
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
    },
    {
        "type": "function",
        "function": {
            "name": "extract_keywords",
            "description": "从输入文本中提取高频关键词，适合快速提炼主题词。",
            "parameters": ExtractKeywordsArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "redact_sensitive_text",
            "description": "对文本中的邮箱和手机号进行脱敏处理。",
            "parameters": RedactSensitiveTextArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_report_file",
            "description": "删除授权目录中的文件（高风险操作）。",
            "parameters": DeleteReportFileArgs.model_json_schema(),
        },
    },
]
