import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

from backend.tools import OPENAI_TOOLS, TOOL_REGISTRY, get_active_audit_entries, get_active_permission_state, set_active_session


SYSTEM_PROMPT = """
你是一个轻量级事务型 AI Agent，擅长调查网络信息、分析简单趋势数据、整理并输出结论。

工作原则：
1. 当任务需要外部信息时，优先调用 search_internet。
2. 当用户提供 JSON 数值数据且需要统计分析时，调用 analyze_trend_data。
3. 任何保存/编辑/生成报告等文件操作前，必须先调用 request_report_folder_access，再调用 confirm_report_folder_access，获得明确授权后才能调用文件工具。
4. 当用户明确要求生成报告、保存结果、沉淀结论时，满足授权流程后调用 generate_markdown_report。
5. 若用户要求导出报告但未明确格式，先询问用户在 md/docx/pdf 中选择一种，再调用 save_report。
6. 优先使用 save_report 进行统一导出；仅在用户明确要求仅生成 Markdown 草稿时调用 generate_markdown_report。
7. 你可以多次调用工具，直到获得足够信息后再给出最终答复。
8. 如果工具执行失败，请根据错误信息修正调用参数并继续尝试，或向用户说明限制。
9. 最终回答请使用中文，尽量清晰、结构化，并结合工具结果。
""".strip()

MAX_TOOL_ROUNDS = 8


class ChatMessage(BaseModel):
    role: str
    content: str


class SessionState(BaseModel):
    file_access_granted: bool = Field(default=False, description="当前会话是否已授权文件访问。")
    allowed_report_folder: Optional[str] = Field(default=None, description="当前会话被授权的报告目录。")


class ChatRequest(BaseModel):
    api_key: str = Field(..., description="用户自带的 DeepSeek API Key。")
    message: str = Field(..., description="本轮用户输入。")
    history: List[ChatMessage] = Field(default_factory=list, description="历史对话。")
    model: str = Field(default="deepseek-chat", description="要调用的 DeepSeek 模型。")
    session_id: str = Field(default="default", description="当前会话 ID，用于持久化工具授权状态。")
    session_state: SessionState = Field(default_factory=SessionState, description="当前会话权限状态。")


class ToolLog(BaseModel):
    timestamp: str
    tool_name: str
    arguments: Dict[str, Any]
    output: str
    success: bool
    error_category: Optional[Literal["permission_denied", "path_violation", "format_unsupported", "io_failure"]] = None


class AuditEntry(BaseModel):
    timestamp: str
    operation: str
    target_file: Optional[str]
    allowed_folder: Optional[str]
    authorization_state: str
    decision: str
    error_category: Optional[Literal["permission_denied", "path_violation", "format_unsupported", "io_failure"]] = None
    summary: str


ErrorCategory = Literal["permission_denied", "path_violation", "format_unsupported", "io_failure"]


class ChatResponse(BaseModel):
    answer: str
    tool_logs: List[ToolLog]
    audit_entries: List[AuditEntry]
    session_state: SessionState


app = FastAPI(title="Lightweight AI Agent MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_messages(history: List[ChatMessage], user_message: str) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        if item.role not in {"user", "assistant"}:
            continue
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": user_message})
    return messages


def create_client(api_key: str) -> OpenAI:
    key = api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="DeepSeek API Key 不能为空。")

    return OpenAI(api_key=key, base_url="https://api.deepseek.com")


def _normalize_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: List[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif getattr(block, "type", None) == "text":
                texts.append(getattr(block, "text", ""))
        return "\n".join(texts)
    return ""


def _safe_parse_arguments(raw_arguments: Optional[str]) -> Dict[str, Any]:
    if not raw_arguments:
        return {}
    try:
        return json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {"raw_input": raw_arguments}


def _current_session_state() -> SessionState:
    state = get_active_permission_state()
    return SessionState(
        file_access_granted=bool(state.get("file_access_granted", False)),
        allowed_report_folder=state.get("allowed_report_folder"),
    )


def _categorize_error(exc: Exception) -> Optional[ErrorCategory]:
    text = str(exc)
    if isinstance(exc, PermissionError):
        if "不在授权目录" in text or "目录穿越" in text:
            return "path_violation"
        return "permission_denied"
    if isinstance(exc, ValueError):
        if "不支持" in text or "仅支持" in text:
            return "format_unsupported"
        if "目录穿越" in text:
            return "path_violation"
    if isinstance(exc, OSError):
        return "io_failure"
    return None


def _build_audit_entries() -> List[AuditEntry]:
    entries: List[AuditEntry] = []
    for item in get_active_audit_entries():
        operation = str(item.get("operation", "unknown"))
        decision = str(item.get("decision", "unknown"))
        target_file = item.get("target_file")
        summary = f"{operation}: {decision}"
        if target_file:
            summary += f" ({target_file})"
        entries.append(
            AuditEntry(
                timestamp=str(item.get("timestamp", "")),
                operation=operation,
                target_file=str(target_file) if target_file else None,
                allowed_folder=str(item.get("allowed_folder")) if item.get("allowed_folder") else None,
                authorization_state=str(item.get("authorization_state", "unknown")),
                decision=decision,
                error_category=item.get("error_category"),
                summary=summary,
            )
        )
    return entries


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/agent", response_model=ChatResponse)
def run_agent(request: ChatRequest) -> ChatResponse:
    client = create_client(request.api_key)
    set_active_session(request.session_id, request.session_state.model_dump())
    messages = build_messages(request.history, request.message)
    tool_logs: List[ToolLog] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=request.model,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        assistant_message = response.choices[0].message

        assistant_payload: Dict[str, Any] = {
            "role": "assistant",
            "content": _normalize_content(assistant_message.content),
        }
        if assistant_message.tool_calls:
            assistant_payload["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in assistant_message.tool_calls
            ]
        messages.append(assistant_payload)

        if not assistant_message.tool_calls:
            final_answer = _normalize_content(assistant_message.content).strip()
            return ChatResponse(
                answer=final_answer or "模型没有返回文本结果。",
                tool_logs=tool_logs,
                audit_entries=_build_audit_entries(),
                session_state=_current_session_state(),
            )

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            arguments = _safe_parse_arguments(tool_call.function.arguments)
            tool_func = TOOL_REGISTRY.get(tool_name)

            if tool_func is None:
                output = f"工具 {tool_name} 不存在。"
                success = False
                error_category: Optional[ErrorCategory] = "io_failure"
            else:
                try:
                    output = str(tool_func(**arguments))
                    success = True
                    error_category = None
                except PermissionError as exc:
                    output = str(exc)
                    success = False
                    error_category = _categorize_error(exc)
                except Exception as exc:
                    output = f"工具执行失败: {exc}"
                    success = False
                    error_category = _categorize_error(exc)

            tool_logs.append(
                ToolLog(
                    timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    tool_name=tool_name,
                    arguments=arguments,
                    output=output,
                    success=success,
                    error_category=error_category,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": output,
                }
            )

    raise HTTPException(status_code=500, detail="Agent 工具调用轮次超限，已中止执行。")
