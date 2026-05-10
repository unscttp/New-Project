from pydantic import BaseModel, Field

from ..shared.pathing import SCOPED_PATH_DENIED_TEXT, resolve_scoped_path


class ReadReportFileArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")
    filename: str = Field(..., description="仅文件名，例如 summary.md。")


def read_report_file(allowed_folder: str, filename: str) -> str:
    target_path = resolve_scoped_path(allowed_folder, filename)
    if not target_path.exists():
        raise FileNotFoundError(f"文件不存在：{target_path.name}")
    if not target_path.is_file():
        raise PermissionError(SCOPED_PATH_DENIED_TEXT)
    return target_path.read_text(encoding="utf-8")
