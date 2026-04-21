from typing import Callable, Literal, Optional


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
