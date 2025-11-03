# Vahan-Rakshak

This repository contains the Vahan-Rakshak project. The primary purpose of this project is to integrate with IBM watsonx Orchestrate — it provides an HTTP API and integration layer that invokes watsonx Orchestrate Agents for decisioning and multi-skill workflows.

## Quick links
- API folder: `api/` (contains the application package, Dockerfile and helper files)
- API app object: `api/src/api/server.py` (exposed as `src.api.server:app` when running uvicorn)

---

## API — Overview (api/)

The API is implemented as a Python web application (FastAPI + uvicorn). It can be run directly for development, packaged into a container for production, or installed as a Python package for deployments.

### At-a-glance
- Location: `api/`
- Application package: `api/src/` (the FastAPI app object is exposed at `src.api.server:app`).
- Dev entrypoint: `api/main.py` (packaging/entry script).
- Dependencies: `api/requirements.txt`.
- Container: `api/Dockerfile`.
- API reference: `api/docs/swagger.json` and `api/postman/Vahan-Rakshak.postman_collection.json`.

### Repository structure (relevant files)

- `api/main.py` — project-level entrypoint used by some deploy systems.
- `api/requirements.txt` — pinned Python dependencies for the API.
- `api/Dockerfile` — build instructions for container images.
- `api/render.yaml` — deployment config for Render.com (optional).
- `api/setup.py` — packaging metadata for installing the package (editable installs).
- `api/src/` — application package:
  - `api/src/api/server.py` — the FastAPI app instance (exposed as `app`).
  - `api/src/models/`, `api/src/tools/`, `api/src/iot/` — domain modules used by the API.
- `api/tests/` — pytest-based tests for the API (integration/unit tests).
- `api/docs/`, `api/postman/`, `api/scripts/` — documentation and helper scripts.

### Quick start — Development (Windows, cmd.exe)

1. Create and activate a virtual environment (recommended):

```cmd
python -m venv venv
venv\Scripts\activate
```

2. From the `api/` folder, install dependencies:

```cmd
cd api
pip install -r requirements.txt
```

3. Run the API in development mode (hot reload):

```cmd
venv\Scripts\python.exe -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Notes:
- The `uvicorn` command above points to the FastAPI `app` object by module path: `src.api.server:app`.
- If imports fail when running from `api/`, try running from the repository root or install the package in editable mode:

```cmd
pip install -e .
```

### Configuration / Environment

The API reads configuration primarily from environment variables. Common variables used by this project (adjust as needed):

- `HOST` — host to bind (default `0.0.0.0` when using uvicorn)
- `PORT` — HTTP port (default `8000`)
- `LOG_LEVEL` — logging level (e.g., `info`, `debug`)
- `ENV` — runtime environment (e.g., `development`, `production`)

Set them in PowerShell/CMD before starting the server, or use a `.env` loader if available in the codebase.

Windows (cmd.exe) example:

```cmd
set PORT=8000
set LOG_LEVEL=debug
venv\Scripts\python.exe -m uvicorn src.api.server:app --host 0.0.0.0 --port %PORT% --reload
```

### Run in Docker (production-ish)

1. Build the image (from `api/`):

```cmd
cd api
docker build -t vahan-rakshak-api:latest .
```

2. Run the container locally on port 8000:

```cmd
docker run --rm -p 8000:8000 --env PORT=8000 vahan-rakshak-api:latest
```

Review the `api/Dockerfile` for environment vars or non-root runtime specifics.

### Tests

Run unit/integration tests with pytest from the `api/` folder (recommended in the activated venv):

```cmd
cd api
pip install -r requirements.txt
venv\Scripts\python.exe -m pytest -q
```

If tests touch external services (MQTT, Watson, regulators), consider running them with mocks or using the integration helpers in `api/scripts/`.

### API docs and examples

- Interactive docs (when server is running):
  - OpenAPI UI (Swagger): http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc (if configured)
- Offline/OpenAPI file: `api/docs/swagger.json`.
- Postman collection: `api/postman/Vahan-Rakshak.postman_collection.json`.

Example curl (health check) — adjust path to match your app's health endpoint:

```cmd
curl http://localhost:8000/health
```

Example curl (JSON POST) — replace `/api/some-endpoint` with a real endpoint from the project:

```cmd
curl -X POST http://localhost:8000/api/some-endpoint -H "Content-Type: application/json" -d "{\"key\": \"value\"}"
```

### CI / Deployment hints

- The repo contains `api/render.yaml` for Render.com. Adjust env vars/secret handling per your provider.
- Prefer pinned dependencies from `api/requirements.txt` for reproducible builds.
- Consider adding a small health endpoint that returns 200 quickly so orchestrators can probe the container.

### Troubleshooting

- Import errors: ensure you run commands from the repository root or install the package (`pip install -e .`).
- Port in use: change the `--port` value or stop the process binding the port.
- Missing dependencies: re-run `pip install -r api/requirements.txt` inside the active venv.

### Contributing

- See repository-level CONTRIBUTING or open an issue/pr describing the change.
- Keep changes small and add tests for new behavior.

### Maintainers / Contact

- See project root for maintainers, issue tracker, and contributor list.

---
If you'd like, I can also:

- Add ready-to-run example curl/Postman requests for the main endpoints in this repo.
- Add a short `docker-compose.yml` to run the API with mocked dependencies.
- Keep a shorter project-level README that links to `api/README.md` instead (if you'd prefer the API README to remain in `api/`).

## IBM watsonx Orchestrate Agents (integration)

This project can optionally delegate decision-making and workflow to IBM watsonx Orchestrate Agents (referred to in the codebase as "watsonx"). The orchestration layer lets you offload complex agentic reasoning, long-running workflows, and multi-skill coordination to IBM's Orchestrate platform while keeping local agents available for development and fallbacks.

What this repo provides
- `src/watsonx_agent_caller.py` — the module that performs authenticated calls to the watsonx Orchestrate API and invokes configured agents (Guardian, Gatekeeper, etc.).
- `src/agents/` — local agent implementations (Gatekeeper, Guardian, and supporting skills) that can be used instead of or alongside remote agents.
- `architecture/mermaid_architetecture.mermaid` — architecture diagram showing how FastAPI invokes the Watson caller and agents.

How it works
- When enabled, the server exchanges an API key / IAM token with the watsonx service and calls the Orchestrate API with an agent identifier and input payload.
- The remote agent runs the configured workflow/skills and returns a structured response which the server uses to determine actions (for example, dispatch SOS, mark cargo non-compliant, or trigger vehicle actuators).

Environment variables (key)
- `WATSONX_API_URL` — URL of the watsonx Orchestrate API endpoint.
- `WATSONX_API_KEY` — API key, IAM token or secret used to authenticate to watsonx (store securely; do not commit).
- `WATSONX_ENABLED` — flag (true/false) to enable remote orchestration. If not set or false, the server falls back to local/in-repo agents.
- `GUARDIAN_AGENT_ID`, `GATEKEEPER_AGENT_ID` — identifiers for the remote agents to call.


Example (enable watsonx for local run)

```cmd
set WATSONX_API_URL=https://api.us-south.watsonx.ai/orchestrate/v1
set WATSONX_API_KEY=<REDACTED_KEY>
set WATSONX_ENABLED=true
set GUARDIAN_AGENT_ID=guardian-agent-id
venv\Scripts\python.exe -m uvicorn src.api.server:app --reload
```

Implementation notes
- Look at `src/watsonx_agent_caller.py` for how requests are formed, authenticated, and parsed. The module includes error handling to revert to local decisioning on failures.
- Agent identifiers and the exact request/response schema are influenced by the Orchestrate workspace and agent configuration; adapt `GUARDIAN_AGENT_ID`/`GATEKEEPER_AGENT_ID` to your deployed agents.

Where to go next
- If you want, I can:
  - Extract example request/response payloads from `src/watsonx_agent_caller.py` and add them here.
  - Add a small mock server or a Postman example that emulates the Orchestrate API for local testing.
  - Add CI steps that inject a test token and validate the watsonx path in a gated integration test.
