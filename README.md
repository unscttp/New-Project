# Simple Workflow

## 1. Purpose
This repository hosts a lightweight AI Agent MVP with a web chat interface, a FastAPI backend, and an optional Snake easter egg fallback.

## 2. Audience
- Developers extending frontend/backend features.
- Maintainers operating local development and release workflows.
- Product/QA reviewers validating runtime behavior and integration points.

## 3. Inputs/Outputs (Interfaces)
### Architecture map
- `frontend/`: Next.js-based chat UI and static assets.
- `backend/`: FastAPI service, tool wiring, and prompt/tool configuration.
- `easter-eggs/`: archived or optional non-core experiences (including Snake static source).

### Startup prerequisites
- Python 3.10+ (backend runtime)
- Node.js 18+ and npm/pnpm (frontend runtime)
- Access to required model/API credentials via environment variables (project-local `.env` as applicable)

### API entrypoints
- Backend service root: FastAPI app in `backend/` (run according to backend server command in project scripts).
- Core chat/API routes: exposed by the backend FastAPI router layer in `backend/`.
- Frontend runtime endpoint: Next.js app in `frontend/`, which calls backend chat APIs.

### Runtime behavior output
- Primary output: conversational responses in the web UI.
- Fallback output: if chat request fails due to network issues, UI can offer the Snake easter egg.
  - Runtime copy: `frontend/public/snake/`
  - Archived static version: `easter-eggs/snake-static/`

## 4. Constraints/Policies
- Keep architecture boundaries clear (`frontend` UI, `backend` service/tools, `easter-eggs` optional extras).
- Avoid coupling product-critical behavior to easter-egg components.
- Document any new API surface and environment variables in this README when changed.

## 5. Examples
- **Run local backend**: start FastAPI service from `backend/` using project-defined run command.
- **Run local frontend**: start Next.js dev server from `frontend/`, pointing to local backend API.
- **Network failure path**: intentionally block backend connectivity to verify Snake fallback prompt appears.

## 6. Change log / maintenance notes
- Keep this file synchronized with actual folder layout and runtime entrypoints.
- When adding/removing top-level modules, update the architecture map in the same PR.
- Prefer incremental, dated notes in PR descriptions for operational changes affecting setup.

## 7. Naming conventions
- Use one tool function per file where practical.
- Tool module filenames should mirror the primary function name they implement.
- Avoid catch-all names like `skills.py`, `helpers.py`, or `misc.py` for tool modules.
- Any tool module rename must include corresponding import updates in `backend/tools/__init__.py` and documentation updates in `backend/tools/TOOLS.md`.
