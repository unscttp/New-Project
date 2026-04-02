# Tool Catalog and Risk Levels

## Risk-level policy
- `low`: can use only Low risk tools.
- `medium`: can use Low risk + Medium risk tools.
- `high`: can use all tools (Low/Medium/High).

## Tools
| Name | Function | Risk level |
|---|---|---|
| search_internet | Search public web information and return summarized results. | low |
| analyze_trend_data | Parse JSON numeric data and output summary statistics. | low |
| request_report_folder_access | Request folder-authorization intent before any file operation. | low |
| confirm_report_folder_access | Persist user authorization decision for file operations. | low |
| generate_markdown_report | Generate a Markdown report in an authorized folder. | low |
| save_report | Export report in `md`, `docx`, or `pdf`. | low |
| save_report_file | Save raw report content to a file. | low |
| read_report_file | Read raw report content from a file. | low |
| edit_report_file | Overwrite an existing report file with updated content. | medium |
| read_report | Read formatted report content (`md`/`docx`) with metadata. | medium |
| edit_report | Edit report content with append/rewrite/replace_section modes. | medium |
| list_report_files | List report files in authorized folder. | low |
| select_tool_risk_level | Set session risk-level gate (`low`/`medium`/`high`). | low |

## Folder layout
- `tools/Low risk/creation.py`: low-risk file creation/save logic.
- `tools/Medium risk/editing.py`: medium-risk file editing logic.
- `tools/High risk/`: reserved for future high-risk tools.
