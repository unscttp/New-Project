import json
from typing import Callable

from docx import Document


from pydantic import BaseModel, Field


class ReadReportArgs(BaseModel):
    file_name: str = Field(..., description="仅文件名，例如 summary.md。")
    folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")


def read_report(
    file_name: str,
    folder: str,
    *,
    resolve_scoped_path: Callable[[str, str], object],
    scoped_path_denied_text: str,
    ensure_supported_read_extension: Callable[[object], str],
) -> str:
    target_path = resolve_scoped_path(folder, file_name)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(scoped_path_denied_text)

    ext = ensure_supported_read_extension(target_path)
    if ext == ".md":
        content = target_path.read_text(encoding="utf-8")
        return json.dumps(
            {
                "file_name": target_path.name,
                "format": "md",
                "line_count": len(content.splitlines()),
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )

    doc = Document(target_path)
    paragraphs = [p.text for p in doc.paragraphs]
    return json.dumps(
        {
            "file_name": target_path.name,
            "format": "docx",
            "paragraph_count": len(paragraphs),
            "content": "\n".join(paragraphs),
        },
        ensure_ascii=False,
        indent=2,
    )
