# Tools Documentation

## 1. Purpose
Define the backend tool catalog, risk model, and maintenance rules for tool governance.

## 2. Audience
- Backend developers adding/updating tools.
- Prompt and orchestration maintainers who reference tool names.
- Reviewers validating risk-gating and file-operation safeguards.

## 3. Inputs/Outputs (Interfaces)
### Source of truth
Tool names documented here **must exactly match** the `TOOL_REGISTRY` keys in `backend/tools/__init__.py`. If there is any conflict, `TOOL_REGISTRY` is authoritative and this document must be updated immediately.

### Risk-level policy
- `low`: can use only Low risk tools.
- `medium`: can use Low risk + Medium risk tools.
- `high`: can use all tools (Low/Medium/High).

### Tools
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
| list_report_files | List report files in authorized folder. | low |
| select_tool_risk_level | Set session risk-level gate (`low`/`medium`/`high`). | low |
| extract_keywords | Extract top-k keywords from text. | low |
| edit_report_file | Overwrite an existing report file with updated content. | medium |
| read_report | Read formatted report content (`md`/`docx`) with metadata. | medium |
| edit_report | Edit report content with append/rewrite/replace_section modes. | medium |
| redact_sensitive_text | Mask emails and phone numbers in free text. | medium |
| delete_report_file | Delete a report file in the authorized folder. | high |

### Folder layout
- `tools/low_risk/creation.py`: low-risk file creation/save logic.
- `tools/low_risk/extract_keywords.py`: low-risk text processing (`extract_keywords`).
- `tools/medium_risk/editing.py`: medium-risk file editing logic.
- `tools/medium_risk/redact_sensitive_text.py`: medium-risk text transformation (`redact_sensitive_text`).
- `tools/high_risk/delete_report_file.py`: high-risk destructive operation (`delete_report_file`).

## 4. Constraints/Policies
- Any file operation flow must preserve explicit authorization semantics in tool design and prompting.
- Risk classifications require review whenever capability scope changes.
- Avoid introducing undocumented tools; add both implementation and docs in the same change.

## 5. Examples
- **Adding a tool**: implement tool, register in `TOOL_REGISTRY`, then append row in the Tools table.
- **Renaming a tool**: update `TOOL_REGISTRY` key first, then update all prompt/tool references and this document.
- **Risk escalation**: if tool gains write/delete behavior, re-evaluate and potentially move from `low` to `medium`/`high`.

## 6. Change log / maintenance notes
- Treat this file as a maintained interface spec, not a narrative guide.
- Reconcile this doc against `backend/tools/__init__.py` during code review.
- Keep descriptions concise and behavior-focused so prompts can safely depend on them.
