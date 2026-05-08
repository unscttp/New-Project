"""Create/update tool metadata without editing backend/tools/__init__.py manually."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent / "tool_registry.json"


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(payload: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_tool(name: str, risk_level: str, callable_path: str, args_model_path: str, description: str) -> None:
    payload = load_registry()
    tools = payload.setdefault("tools", [])
    entry = {
        "name": name,
        "risk_level": risk_level,
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
