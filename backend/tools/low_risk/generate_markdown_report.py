from pydantic import BaseModel, Field

from ..shared.audit import get_active_permission_state
from ..shared.pathing import assert_access_granted_and_scoped, safe_report_path


class GenerateMarkdownReportArgs(BaseModel):
    title: str = Field(..., description="Markdown 报告标题。")
    content: str = Field(..., description="Markdown 报告正文内容。")


def generate_markdown_report(title: str, content: str) -> str:
    if not title.strip():
        raise ValueError("title 不能为空。")
    folder = str(get_active_permission_state().get("allowed_report_folder") or "")
    report_dir = assert_access_granted_and_scoped(folder)
    report_path = safe_report_path(title, report_dir)
    report_path.write_text(f"# {title.strip()}\n\n{content.strip()}\n", encoding="utf-8")
    return f"报告已生成：{report_path}"
