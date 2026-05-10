from typing import Callable


from pydantic import BaseModel, Field


class ReadReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")


def read_report_file(
    allowed_folder: str,
    filename: str,
    *,
    resolve_scoped_path: Callable[[str, str], object],
    scoped_path_denied_text: str,
) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(scoped_path_denied_text)
    return target_path.read_text(encoding="utf-8")
