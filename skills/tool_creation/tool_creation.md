# tool_creation.md

This skill standardizes tool onboarding so new tools can be registered without editing Python registries.

## Command template
```bash
python backend/tools/tool_creation.py \
  --name "your_tool_name" \
  --risk-level "low|medium|high" \
  --args-model "YourArgsModel" \
  --description "User-facing tool description"
```

## Expected result
- `backend/tools/tool_registry.json` is updated (insert or update by `name`).
- Runtime registry + OpenAI tools are loaded from JSON by `backend/tools/__init__.py`.

## Manual follow-up checklist
- [ ] Callable exists and is wired in `TOOL_CALLABLES`.
- [ ] Args model exists in `backend/tools/__init__.py`.
- [ ] Risk classification in `backend/tools/TOOLS.md` matches JSON.
