"use client";

import { FormEvent, useEffect, useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ToolLog = {
  timestamp: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  output: string;
  success: boolean;
  error_category?: "permission_denied" | "path_violation" | "format_unsupported" | "io_failure" | null;
};

type AuditEntry = {
  timestamp: string;
  operation: string;
  target_file?: string | null;
  allowed_folder?: string | null;
  authorization_state: string;
  decision: string;
  error_category?: "permission_denied" | "path_violation" | "format_unsupported" | "io_failure" | null;
  summary: string;
};

type SessionState = {
  file_access_granted: boolean;
  allowed_report_folder?: string | null;
};

type ApprovalRequest = {
  purpose: string;
  folder: string;
};

type OperationType = "save" | "edit" | "review";
type FileFormat = "md" | "docx" | "pdf";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";
const NETWORK_FALLBACK_MESSAGE = "网络出现问题，需要玩一会贪吃蛇来等待一下吗？";

function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError) {
    return true;
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    return (
      message.includes("failed to fetch") ||
      message.includes("networkerror") ||
      message.includes("load failed") ||
      message.includes("network request failed")
    );
  }

  return false;
}

export default function HomePage() {
  const [sessionId, setSessionId] = useState("default");
  const [sessionState, setSessionState] = useState<SessionState>({
    file_access_granted: false,
    allowed_report_folder: null,
  });
  const [apiKey, setApiKey] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "这里是一个轻量级 AI Agent MVP。你可以先在上方填入 DeepSeek API Key，再让我帮你搜索、分析 JSON 数据或生成 Markdown 报告。",
    },
  ]);
  const [toolLogs, setToolLogs] = useState<ToolLog[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [pendingApproval, setPendingApproval] = useState<ApprovalRequest | null>(null);
  const [approvalFolder, setApprovalFolder] = useState("");
  const [approvalFilename, setApprovalFilename] = useState("");
  const [approvalOperation, setApprovalOperation] = useState<OperationType>("save");
  const [approvalFormat, setApprovalFormat] = useState<FileFormat>("md");
  const [denyReason, setDenyReason] = useState("");
  const [validationError, setValidationError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedKey = window.localStorage.getItem("deepseek_api_key");
    const savedSessionId = window.localStorage.getItem("agent_session_id");
    if (savedSessionId) {
      setSessionId(savedSessionId);
    } else {
      const nextId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}`;
      window.localStorage.setItem("agent_session_id", nextId);
      setSessionId(nextId);
    }
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, []);

  useEffect(() => {
    if (apiKey) {
      window.localStorage.setItem("deepseek_api_key", apiKey);
    } else {
      window.localStorage.removeItem("deepseek_api_key");
    }
  }, [apiKey]);

  function extractPendingApproval(logs: ToolLog[]): ApprovalRequest | null {
    const requestLog = [...logs].reverse().find((item) => item.tool_name === "request_report_folder_access");
    if (!requestLog?.success) {
      return null;
    }
    try {
      const parsed = JSON.parse(requestLog.output) as {
        status?: string;
        purpose?: string;
        folder?: string;
      };
      if (parsed.status === "awaiting_user_confirmation" && parsed.folder) {
        return {
          purpose: parsed.purpose || "文件操作",
          folder: parsed.folder,
        };
      }
    } catch {
      return null;
    }
    return null;
  }

  function extractDenyReason(logs: ToolLog[]): string {
    const latestDenied = [...logs].reverse().find((item) => !item.success && item.error_category);
    if (!latestDenied) {
      return "";
    }
    if (latestDenied.error_category === "permission_denied") {
      return `权限被拒绝：${latestDenied.output}`;
    }
    if (latestDenied.error_category === "path_violation") {
      return `路径校验失败：${latestDenied.output}`;
    }
    if (latestDenied.error_category === "format_unsupported") {
      return `文件格式不支持：${latestDenied.output}`;
    }
    return `工具执行失败：${latestDenied.output}`;
  }

  function validateApprovalFields(folder: string, filename: string): string {
    if (!folder.trim()) {
      return "目录不能为空。";
    }
    if (folder.includes("..")) {
      return "目录中不能包含 ..。";
    }
    if (filename.trim() && !/^[\w.\-]+$/.test(filename.trim())) {
      return "文件名仅允许字母、数字、下划线、中划线和点。";
    }
    return "";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiKey.trim()) {
      setError("请先填写 DeepSeek API Key。");
      return;
    }
    if (!input.trim()) {
      setError("请输入消息内容。");
      return;
    }
    if (pendingApproval) {
      setError("请先在授权卡片中选择允许或拒绝，再继续发送任务。");
      return;
    }

    const history = [...messages];
    const userMessage: Message = { role: "user", content: input.trim() };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          api_key: apiKey.trim(),
          message: userMessage.content,
          history,
          model: "deepseek-chat",
          session_id: sessionId,
          session_state: sessionState,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "请求失败，请检查后端日志。");
      }

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.answer || "模型没有返回结果。",
        },
      ]);
      setToolLogs(Array.isArray(data.tool_logs) ? data.tool_logs : []);
      setAuditEntries(Array.isArray(data.audit_entries) ? data.audit_entries : []);
      if (data.session_state) {
        setSessionState(data.session_state);
      }
      const logs = Array.isArray(data.tool_logs) ? data.tool_logs : [];
      const nextPending = extractPendingApproval(logs);
      setPendingApproval(nextPending);
      if (nextPending) {
        setApprovalFolder(nextPending.folder);
      }
      setDenyReason(extractDenyReason(logs));
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "发生未知错误，请稍后再试。";
      setError(message);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `请求失败：${message}`,
        },
      ]);

      if (isNetworkError(requestError) && window.confirm(NETWORK_FALLBACK_MESSAGE)) {
        window.location.href = "/snake/";
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleApprovalDecision(granted: boolean) {
    if (!pendingApproval || loading) {
      return;
    }
    const validation = validateApprovalFields(approvalFolder, approvalFilename);
    if (validation) {
      setValidationError(validation);
      return;
    }
    setValidationError("");
    const message = [
      granted ? "我同意授权该目录。" : "我拒绝本次目录授权。",
      `请调用 confirm_report_folder_access(granted=${granted ? "true" : "false"}, folder="${approvalFolder}")。`,
      `本次意图操作：${approvalOperation}`,
      `文件格式：${approvalFormat}`,
      `目标文件名：${approvalFilename || "未指定"}`,
    ].join("\n");
    const history = [...messages];
    const approvalMessage: Message = { role: "user", content: message };
    setMessages((current) => [...current, approvalMessage]);
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          api_key: apiKey.trim(),
          message: approvalMessage.content,
          history,
          model: "deepseek-chat",
          session_id: sessionId,
          session_state: {
            file_access_granted: false,
            allowed_report_folder: null,
          },
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "请求失败，请检查后端日志。");
      }
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.answer || "模型没有返回结果。",
        },
      ]);
      const logs = Array.isArray(data.tool_logs) ? data.tool_logs : [];
      setToolLogs(logs);
      setAuditEntries(Array.isArray(data.audit_entries) ? data.audit_entries : []);
      if (data.session_state) {
        setSessionState(data.session_state);
      }
      const nextPending = extractPendingApproval(logs);
      setPendingApproval(nextPending);
      if (!nextPending) {
        setApprovalFilename("");
      }
      setDenyReason(extractDenyReason(logs));
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "发生未知错误，请稍后再试。";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function revokeAccess() {
    setSessionState({
      file_access_granted: false,
      allowed_report_folder: null,
    });
    setPendingApproval(null);
    setDenyReason("你已在前端撤销授权。发送下一条消息时会同步到后端会话。");
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#fef3c7,_#fff7ed_35%,_#ffffff_70%)] px-4 py-10 text-slate-900">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <section className="rounded-3xl border border-amber-200 bg-white/85 p-6 shadow-[0_24px_80px_-32px_rgba(180,83,9,0.35)] backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-700">
            Agent Settings
          </p>
          <h1 className="mt-3 font-serif text-3xl text-slate-950">轻量级 AI Agent MVP</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            API Key 仅保存在浏览器本地，发请求时会以 BYOK 模式传给 FastAPI 后端。
          </p>
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
            <p className="font-semibold text-slate-900">当前会话授权目录</p>
            <p className="mt-1 font-mono">
              {sessionState.file_access_granted && sessionState.allowed_report_folder
                ? sessionState.allowed_report_folder
                : "未授权"}
            </p>
            <button
              type="button"
              onClick={revokeAccess}
              className="mt-3 rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              revoke access
            </button>
          </div>

          <label className="mt-6 block text-sm font-medium text-slate-700">DeepSeek API Key</label>
          <textarea
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="sk-..."
            className="mt-2 min-h-32 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-amber-400 focus:bg-white"
          />

          <div className="mt-6 rounded-2xl border border-dashed border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">可直接尝试：</p>
            <p className="mt-2">1. 搜索一下最近 AI Agent 的热门趋势</p>
            <p className="mt-1">
              2. 分析这段 JSON 数据：<code>{`[{"value":12}, {"value":30}]`}</code>
            </p>
            <p className="mt-1">3. 整理结论并生成一份 Markdown 报告</p>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.3)] backdrop-blur">
          <div className="flex min-h-[60vh] flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto rounded-2xl bg-slate-50/80 p-4">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
                    message.role === "user"
                      ? "ml-auto bg-slate-900 text-white"
                      : "bg-white text-slate-800"
                  }`}
                >
                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.24em] opacity-60">
                    {message.role === "user" ? "User" : "Agent"}
                  </p>
                  <pre className="whitespace-pre-wrap font-sans">{message.content}</pre>
                </div>
              ))}

              {loading && (
                <div className="max-w-[85%] rounded-2xl bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                  Agent 正在思考并可能调用工具，请稍候...
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} className="mt-4 space-y-3">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="输入任务，例如：先搜索 Agent 热词，再整理为报告。"
                className="min-h-28 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-amber-400"
              />
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs text-slate-500">
                  后端地址：<span className="font-mono">{API_BASE_URL}</span>
                </p>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-full bg-amber-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:bg-amber-200"
                >
                  {loading ? "处理中..." : "发送"}
                </button>
              </div>
            </form>

            {error && (
              <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {pendingApproval && (
              <div className="mt-4 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-4 text-sm text-amber-900">
                <p className="font-semibold">需要你确认目录授权</p>
                <p className="mt-1 text-xs text-amber-800">用途：{pendingApproval.purpose}</p>
                <label className="mt-3 block text-xs font-semibold uppercase tracking-wide">目标目录</label>
                <input
                  value={approvalFolder}
                  onChange={(event) => setApprovalFolder(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-amber-300 bg-white px-3 py-2 text-xs text-slate-800 outline-none focus:border-amber-500"
                />
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide">操作类型</label>
                    <select
                      value={approvalOperation}
                      onChange={(event) => setApprovalOperation(event.target.value as OperationType)}
                      className="mt-1 w-full rounded-xl border border-amber-300 bg-white px-3 py-2 text-xs text-slate-800 outline-none"
                    >
                      <option value="save">save</option>
                      <option value="edit">edit</option>
                      <option value="review">review</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide">文件格式</label>
                    <select
                      value={approvalFormat}
                      onChange={(event) => setApprovalFormat(event.target.value as FileFormat)}
                      className="mt-1 w-full rounded-xl border border-amber-300 bg-white px-3 py-2 text-xs text-slate-800 outline-none"
                    >
                      <option value="md">md</option>
                      <option value="docx">docx</option>
                      <option value="pdf">pdf</option>
                    </select>
                  </div>
                </div>
                <label className="mt-3 block text-xs font-semibold uppercase tracking-wide">
                  文件名（可选）
                </label>
                <input
                  value={approvalFilename}
                  onChange={(event) => setApprovalFilename(event.target.value)}
                  placeholder="summary.md"
                  className="mt-1 w-full rounded-xl border border-amber-300 bg-white px-3 py-2 text-xs text-slate-800 outline-none focus:border-amber-500"
                />
                {validationError && <p className="mt-2 text-xs text-red-700">{validationError}</p>}
                <div className="mt-4 flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleApprovalDecision(true)}
                    disabled={loading}
                    className="rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
                  >
                    allow
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApprovalDecision(false)}
                    disabled={loading}
                    className="rounded-full bg-red-500 px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
                  >
                    deny
                  </button>
                </div>
              </div>
            )}

            {denyReason && (
              <div className="mt-4 rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-800">
                <p className="font-semibold">后端拒绝原因</p>
                <p className="mt-1">{denyReason}</p>
                <p className="mt-1 text-xs">请重新授权目录后再执行文件相关操作。</p>
              </div>
            )}

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-700">
                  Tool Logs
                </h2>
                <span className="text-xs text-slate-400">{toolLogs.length} 条</span>
              </div>

              <div className="mt-3 space-y-3">
                {toolLogs.length === 0 ? (
                  <p className="text-sm text-slate-500">当前还没有工具调用记录。</p>
                ) : (
                  toolLogs.map((log, index) => (
                    <div key={`${log.tool_name}-${index}`} className="rounded-2xl bg-white p-4 shadow-sm">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-mono text-sm text-slate-900">{log.tool_name}</p>
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            log.success
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {log.success ? "成功" : "失败"}
                        </span>
                      </div>
                      <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-slate-950 p-3 text-xs text-slate-100">
                        {JSON.stringify(log.arguments, null, 2)}
                      </pre>
                      <pre className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{log.output}</pre>
                      {log.error_category && (
                        <p className="mt-2 text-xs font-medium text-red-600">
                          error_category: {log.error_category}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-700">
                  Audit Trail
                </h2>
                <span className="text-xs text-slate-400">{auditEntries.length} 条</span>
              </div>
              <div className="mt-3 space-y-3">
                {auditEntries.length === 0 ? (
                  <p className="text-sm text-slate-500">暂无审计记录。</p>
                ) : (
                  auditEntries.map((entry, index) => (
                    <div key={`${entry.timestamp}-${index}`} className="rounded-2xl bg-white p-4 shadow-sm">
                      <p className="text-xs text-slate-500">{entry.timestamp}</p>
                      <p className="mt-1 text-sm font-semibold text-slate-900">{entry.summary}</p>
                      <p className="mt-1 text-xs text-slate-600">
                        state: {entry.authorization_state} / decision: {entry.decision}
                      </p>
                      {entry.target_file && (
                        <p className="mt-1 text-xs text-slate-600">file: {entry.target_file}</p>
                      )}
                      {entry.error_category && (
                        <p className="mt-1 text-xs font-medium text-red-600">
                          error_category: {entry.error_category}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
