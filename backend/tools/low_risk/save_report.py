from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..shared.pathing import resolve_report_output_path
from ..shared.report_writers import write_docx_report, write_pdf_report


class SaveReportArgs(BaseModel):
    title: str = Field(..., description="报告标题。")
    content: str = Field(..., description="报告正文，可为 markdown 或纯文本。")
    format: Literal["md", "docx", "pdf"] = Field(..., description="导出格式：md、docx、pdf。")
    folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: Optional[str] = Field(default=None, description="可选文件名（可不含后缀）。为空时自动生成日期+标题文件名。")


def save_report(title: str, content: str, format: Literal["md", "docx", "pdf"], folder: str, filename: Optional[str] = None) -> str:
    title_text = title.strip()
    content_text = content.strip()
    if not title_text or not content_text:
        raise ValueError("title/content 不能为空。")

    target_path = resolve_report_output_path(folder, title_text, format, filename)
    if format == "md":
        target_path.write_text(f"# {title_text}\n\n{content_text}\n", encoding="utf-8")
    elif format == "docx":
        write_docx_report(target_path, title_text, content_text)
    else:
        write_pdf_report(target_path, title_text, content_text)
    return f"报告已导出：{target_path}"
