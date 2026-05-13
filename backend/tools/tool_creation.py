"""Create/update tool metadata and optionally scaffold new tools."""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
from pathlib import Path
from textwrap import dedent

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
    return isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os"


def _is_file_modification_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "open" and len(node.args) > 1:
        mode_arg = node.args[1]
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            return any(flag in mode_arg.value for flag in ("w", "a", "x", "+"))
    if isinstance(func, ast.Attribute):
        return func.attr.lower() in {
            "write_text", "write_bytes", "unlink", "rename", "replace", "mkdir", "rmdir", "remove", "rmtree", "touch",
        }
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
    return "high" if modifies_files else risk_level


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


def scaffold_tool(module_path: str, function_name: str, args_model_name: str, description: str) -> tuple[str, str]:
    if not module_path.startswith("backend.tools."):
        raise ToolSecurityError("module_path must start with backend.tools.")
    if module_path == "backend.tools":
        raise ToolSecurityError("module_path must point to a concrete tool module.")

    file_path = Path(*module_path.split(".")).with_suffix(".py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        raise ToolSecurityError(f"Refusing to overwrite existing module: {file_path}")

    code = dedent(
        f'''\
        from pydantic import BaseModel, Field


        class {args_model_name}(BaseModel):
            text: str = Field(..., description="Input text.")


        def {function_name}(text: str) -> str:
            """{description}"""
            return text
        '''
    )
    file_path.write_text(code, encoding="utf-8")
    callable_path = f"{module_path}:{function_name}"
    args_path = f"{module_path}:{args_model_name}"
    return callable_path, args_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update tool metadata in tool_registry.json")
    parser.add_argument("--name", required=True)
    parser.add_argument("--risk-level", required=True, choices=["low", "medium", "high"])
    parser.add_argument("--callable-path")
    parser.add_argument("--args-model-path")
    parser.add_argument("--description", required=True)
    parser.add_argument("--module-path", help="Scaffold mode: module path like backend.tools.low_risk.my_tool")
    parser.add_argument("--function-name", help="Scaffold mode: function name")
    parser.add_argument("--args-model-name", help="Scaffold mode: args model class name")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    callable_path = args.callable_path
    args_model_path = args.args_model_path

    if args.module_path:
        if not (args.function_name and args.args_model_name):
            raise ToolSecurityError("Scaffold mode requires --function-name and --args-model-name")
        callable_path, args_model_path = scaffold_tool(args.module_path, args.function_name, args.args_model_name, args.description)

    if not callable_path or not args_model_path:
        raise ToolSecurityError("Provide --callable-path/--args-model-path or scaffold arguments.")

    upsert_tool(
        name=args.name,
        risk_level=args.risk_level,
        callable_path=callable_path,
        args_model_path=args_model_path,
        description=args.description,
    )


if __name__ == "__main__":
    main()
