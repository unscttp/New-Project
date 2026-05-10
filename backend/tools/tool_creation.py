"""Create/update tool metadata without editing backend/tools/__init__.py manually."""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent / "tool_registry.json"


class ToolSecurityError(ValueError):
    """Raised when a tool violates creation security constraints."""


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(payload: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")




def _ensure_direct_module_path(import_path: str, *, field_name: str) -> None:
    module_path, _, _ = import_path.partition(":")
    if module_path == "backend.tools":
        raise ToolSecurityError(f"{field_name} must point to a concrete tool module, not backend.tools:*")

def _load_callable(callable_path: str):
    module_path, _, attr_name = callable_path.partition(":")
    if not module_path or not attr_name:
        raise ToolSecurityError("callable_path must use module.path:function_name format")

    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise ToolSecurityError(f"Callable not found: {callable_path}") from exc


def _get_callable_ast(callable_obj) -> ast.AST:
    source = inspect.getsource(callable_obj)
    return ast.parse(source)


def _is_os_function(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id == "os"
    return False


def _is_file_modification_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "open":
        if not node.args:
            return False
        mode_arg = node.args[1] if len(node.args) > 1 else None
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            return any(flag in mode_arg.value for flag in ("w", "a", "x", "+"))
    if isinstance(func, ast.Attribute):
        attr = func.attr.lower()
        write_like = {
            "write_text",
            "write_bytes",
            "unlink",
            "rename",
            "replace",
            "mkdir",
            "rmdir",
            "remove",
            "rmtree",
            "touch",
        }
        return attr in write_like
    return False


def _enforce_tool_security(callable_path: str, risk_level: str) -> str:
    callable_obj = _load_callable(callable_path)
    tree = _get_callable_ast(callable_obj)

    modifies_files = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_os_function(node):
            raise ToolSecurityError("Tool creation blocked: os.* function usage is not allowed.")
        if isinstance(node, ast.Call) and _is_file_modification_call(node):
            modifies_files = True

    if modifies_files:
        return "high"
    return risk_level


def upsert_tool(name: str, risk_level: str, callable_path: str, args_model_path: str, description: str) -> None:
    _ensure_direct_module_path(callable_path, field_name="callable_path")
    _ensure_direct_module_path(args_model_path, field_name="args_model_path")
    payload = load_registry()
    tools = payload.setdefault("tools", [])
    secured_risk_level = _enforce_tool_security(callable_path, risk_level)
    entry = {
        "name": name,
        "risk_level": secured_risk_level,
        "callable_path": callable_path,
        "args_model_path": args_model_path,
        "description": description,
    }
    for tool in tools:
        if tool.get("name") == name:
            tool.update(entry)
            save_registry(payload)
            return

    tools.append(entry)
    save_registry(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update tool metadata in tool_registry.json")
    parser.add_argument("--name", required=True, help="Tool name shown to model callers")
    parser.add_argument("--risk-level", required=True, choices=["low", "medium", "high"])
    parser.add_argument("--callable-path", required=True, help="Import path as module.path:function_name")
    parser.add_argument("--args-model-path", required=True, help="Import path as module.path:ArgsModelClass")
    parser.add_argument("--description", required=True, help="Tool description used by OpenAI tool schema")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    upsert_tool(
        name=args.name,
        risk_level=args.risk_level,
        callable_path=args.callable_path,
        args_model_path=args.args_model_path,
        description=args.description,
    )


if __name__ == "__main__":
    main()
