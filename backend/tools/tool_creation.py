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


def upsert_tool(name: str, risk_level: str, args_model: str, description: str) -> None:
    payload = load_registry()
    tools = payload.setdefault("tools", [])
    for tool in tools:
        if tool.get("name") == name:
            tool.update(
                {
                    "risk_level": risk_level,
                    "args_model": args_model,
                    "description": description,
                }
            )
            save_registry(payload)
            return

    tools.append(
        {
            "name": name,
            "risk_level": risk_level,
            "args_model": args_model,
            "description": description,
        }
    )
    save_registry(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update tool metadata in tool_registry.json")
    parser.add_argument("--name", required=True, help="Tool name (must match function exposed in __init__.py)")
    parser.add_argument("--risk-level", required=True, choices=["low", "medium", "high"])
    parser.add_argument("--args-model", required=True, help="Pydantic args model class name in backend/tools/__init__.py")
    parser.add_argument("--description", required=True, help="Tool description used by OpenAI tool schema")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    upsert_tool(
        name=args.name,
        risk_level=args.risk_level,
        args_model=args.args_model,
        description=args.description,
    )


if __name__ == "__main__":
    main()
