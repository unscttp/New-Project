import json

from pydantic import BaseModel, Field

from ..shared.pathing import ALLOWED_REPORT_EXTENSIONS, assert_access_granted_and_scoped


class ListReportFilesArgs(BaseModel):
    allowed_folder: str = Field(..., description="已授权目录（必须与当前会话授权目录一致）。")


def list_report_files(allowed_folder: str) -> str:
    report_dir = assert_access_granted_and_scoped(allowed_folder)
    files = sorted([i.name for i in report_dir.iterdir() if i.is_file() and i.suffix.lower() in ALLOWED_REPORT_EXTENSIONS])
    return json.dumps({"allowed_folder": str(report_dir), "files": files}, ensure_ascii=False, indent=2)
