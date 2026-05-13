# tool_creation.md

This skill standardizes tool onboarding so new tools can be registered without editing Python registries.

## Command template
```bash
python backend/tools/tool_creation.py \
  --name "your_tool_name" \
  --risk-level "low|medium|high" \
  --callable-path "backend.tools:your_tool" \
  --args-model-path "backend.tools:YourArgsModel" \
  --description "User-facing tool description"
```

## Expected result
- `backend/tools/tool_registry.json` is updated (insert or update by `name`).
- Runtime registry + OpenAI tools are loaded from JSON by `backend/tools/__init__.py`.

## Manual follow-up checklist
- [ ] Callable import path resolves at runtime (`module.path:function_name`).
- [ ] Args model exists in `backend/tools/__init__.py`.
- [ ] Risk classification in `backend/tools/TOOLS.md` matches JSON.


## Scaffold a brand-new tool module
```bash
python backend/tools/tool_creation.py \
  --name "your_tool_name" \
  --risk-level "low" \
  --module-path "backend.tools.low_risk.your_module" \
  --function-name "your_tool" \
  --args-model-name "YourToolArgs" \
  --description "User-facing tool description" \
  --code "$(cat /path/to/generated_tool.py)"
```
This creates a new Python module from scratch (or from the provided `--code`), runs AST validation/security checks, then auto-registers it in `tool_registry.json`.
