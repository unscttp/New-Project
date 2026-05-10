---
name: tool_creation
description: Add or update backend tool metadata using JSON + tool_creation.py workflow without editing __init__.py registries.
---

# Tool Creation Skill

Use this skill when adding, updating, or documenting tools in `backend/tools/`.

## Structure
- `SKILL.md`: entrypoint instructions only.
- `docs/tool_creation.md`: extended reference material.

## Workflow
1. Implement the tool function in `backend/tools/<risk_level>/` and expose wrapper function in `backend/tools/__init__.py`.
2. Define/ensure a matching Pydantic args model class exists in `backend/tools/__init__.py`.
3. Run `python backend/tools/tool_creation.py --name ... --risk-level ... --args-model-path ... --description ...` to update `backend/tools/tool_registry.json`.
4. Verify `backend/tools/TOOLS.md` remains consistent with `tool_registry.json`.
5. If risk scope changed, update governance/prompt docs accordingly.

## Security guardrails
- Tool `name` in JSON must map to a resolvable callable via `callable_path`.
- `args_model_path` must be an import path to a class that supports `model_json_schema()`.
- Tool creation is blocked when AST inspection detects `os.*` function usage.
- Any callable that can modify existing files is automatically recorded as `high` risk.
- Do not manually reintroduce hard-coded `OPENAI_TOOLS` entries in `backend/tools/__init__.py`.
