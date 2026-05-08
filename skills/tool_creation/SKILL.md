---
name: tool_creation
description: Add or update backend tool metadata using JSON + tool_creation.py workflow without editing __init__.py registries.
---

# Tool Creation Skill

Use this skill when adding, updating, or documenting tools in `backend/tools/`.

## Workflow
1. Implement the tool function in `backend/tools/<risk_level>/` and expose wrapper function in `backend/tools/__init__.py`.
2. Define/ensure a matching Pydantic args model class exists in `backend/tools/__init__.py`.
3. Run `python backend/tools/tool_creation.py --name ... --risk-level ... --args-model ... --description ...` to update `backend/tools/tool_registry.json`.
4. Verify `backend/tools/TOOLS.md` remains consistent with `tool_registry.json`.
5. If risk scope changed, update governance/prompt docs accordingly.

## Guardrails
- Tool `name` in JSON must exactly match the callable key used by runtime wrappers.
- `args_model` must be a class name that supports `model_json_schema()`.
- Do not manually reintroduce hard-coded `OPENAI_TOOLS` entries in `backend/tools/__init__.py`.
