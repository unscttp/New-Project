from pathlib import Path
from typing import Callable, Dict


def generate_markdown_report(
    title: str,
    content: str,
    *,
    get_active_permission_state: Callable[[], Dict[str, str]],
    assert_access_granted_and_scoped: Callable[[str], Path],
    safe_report_path: Callable[[str, Path], Path],
) -> str:
    """在授权目录中生成 Markdown 报告，并做路径安全校验。"""
    if not title.strip():
        raise ValueError("title 不能为空。")

    state = get_active_permission_state()
    folder = str(state.get("allowed_report_folder") or "")
    report_dir = assert_access_granted_and_scoped(folder)
    report_path = safe_report_path(title, report_dir)
    markdown = f"# {title.strip()}\n\n{content.strip()}\n"
    report_path.write_text(markdown, encoding="utf-8")
    return f"报告已生成：{report_path}"
