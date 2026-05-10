from typing import Callable, Literal, Optional


from pydantic import BaseModel, Field


class SaveReportArgs(BaseModel):
    title: str = Field(..., description="报告标题。")
    content: str = Field(..., description="报告正文，可为 markdown 或纯文本。")
    format: Literal["md", "docx", "pdf"] = Field(..., description="导出格式：md、docx、pdf。")
    folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: Optional[str] = Field(default=None, description="可选文件名（可不含后缀）。为空时自动生成日期+标题文件名。")


def save_report(
    title: str,
    content: str,
    format: Literal["md", "docx", "pdf"],
    folder: str,
    filename: Optional[str] = None,
    *,
    resolve_report_output_path: Callable[[str, str, str, Optional[str]], object],
    write_docx_report: Callable[[object, str, str], None],
    write_pdf_report: Callable[[object, str, str], None],
) -> str:
    title_text = title.strip()
    if not title_text:
        raise ValueError("title 不能为空。")

    content_text = content.strip()
    if not content_text:
        raise ValueError("content 不能为空。")

    target_path = resolve_report_output_path(folder, title_text, format, filename)
    if format == "md":
        markdown = f"# {title_text}\n\n{content_text}\n"
        target_path.write_text(markdown, encoding="utf-8")
    elif format == "docx":
        write_docx_report(target_path, title_text, content_text)
    elif format == "pdf":
        write_pdf_report(target_path, title_text, content_text)
    else:
        raise ValueError("不支持的 format，必须是 md/docx/pdf。")

    return f"报告已导出：{target_path}"
