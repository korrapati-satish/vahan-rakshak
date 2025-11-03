```markdown
# Vāhan-Rakshak — Backend (src)

This folder contains the FastAPI backend, in-repo agents, and helper tools for the Vāhan-Rakshak prototype (Vehicle Guardian Agent).

Use this README when working inside the `src/` package; run commands from the repository root unless noted otherwise.

## Summary

- FastAPI application that ingests vehicle telemetry and cargo-scan data and either delegates decisioning to IBM watsonx Orchestrate or uses local agents for development and testing.
- Implements Gatekeeper (pre-trip cargo compliance), Guardian (runtime safety), and specialist skills (SpeedMonitor, DriverMonitor, Evacuation).
- Tool adapters expose OpenAPI-backed interfaces to cargo scanners, vehicle actuators, SOS dispatch, and regulator APIs.

## Quickstart (development)

Prerequisites

- Python 3.10+ (virtualenv recommended)
- Git

Install dependencies (from repository root):

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run the API server (from repository root):

```bash
# start via project entrypoint (main.py)
python main.py
# or run uvicorn directly for hot reload during development
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Health check: `GET http://localhost:8000/healthz`

OpenAPI & docs

- Interactive docs: `http://localhost:8000/docs`
- Curated OpenAPI examples: `http://localhost:8000/v1/openapi-examples.json`
- Source OpenAPI bundle: `docs/swagger.json`

## Environment variables (important)

- WATSONX_API_URL — Watsonx Orchestrate endpoint URL (for remote delegation).
- WATSONX_API_KEY — API key/token for Watsonx.
- WATSONX_ENABLED — enable remote delegation to watsonx when present.
- GUARDIAN_AGENT_ID, GATEKEEPER_AGENT_ID — agent identifiers for remote calls.
- FLEET_CONTACT — default fleet contact used by SOS dispatcher.

If Watsonx credentials are missing, the server falls back to local/in-repo behavior where possible; check `src/api/server.py` logs for details.

## Project layout (key files)

- `main.py` — project entry that launches Uvicorn serving the FastAPI app.
- `src/api/server.py` — FastAPI application and HTTP endpoints.
- `src/watsonx_agent_caller.py` — caller that invokes watsonx Orchestrate agents.
- `src/agents/` — Gatekeeper, Guardian and skill agents used for local testing.
- `src/tools/` — cargo scanner, regulator API, safety actuator, SOS dispatcher, etc.
- `src/iot/` — MQTT client and sensor manager for IoT integration.

## Tests

Run tests from the repository root with pytest:

```bash
pip install -r requirements.txt
pytest -q
```

## Architecture

Text-based architecture lives at `architecture/mermaid_architetecture.mermaid` (render with any Mermaid tool). A high-resolution SVG/PNG can be generated with the Mermaid CLI.

## Contributing

Open issues or pull requests. Keep changes small and include tests for behavioral changes.

---

If you'd like, I can add a small `.env.example` or a short `scripts/dev_start.sh` to speed up local runs.

```
