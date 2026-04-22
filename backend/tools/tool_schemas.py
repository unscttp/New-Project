from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class ExtractKeywordsArgs(BaseModel):
    text: str = Field(..., description="要提取关键词的文本内容。")
    top_k: int = Field(default=8, description="返回关键词个数，默认 8。")


class RedactSensitiveTextArgs(BaseModel):
    content: str = Field(..., description="需要脱敏处理的文本内容。")


class DeleteReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="要删除的文件名（仅文件名）。")


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
