# Job Orchestrator Service - Web UI

This folder contains a browser-facing control page and a lightweight Flask bridge for `job-orchestrator-service`.

## Current Web Model

The core backend exposes native gRPC only. Browsers do not talk to that service directly, so this folder adds a small HTTP bridge and a single-page control deck.

Current pieces:

- Native gRPC backend in `server/main.py`
- Browser UI at `web/index.html`
- Python web bridge at `web/app.py`

The bridge exposes browser-friendly endpoints:

- `GET /` serves the control page
- `GET /healthz` reports bridge health and current gRPC target
- `GET /api/overview` returns service metadata and supported commands
- `POST /api/jobs` submits a job
- `GET /api/jobs/<job_id>` gets job status
- `GET /api/jobs/<job_id>/watch` streams updates over Server-Sent Events
- `POST /api/jobs/<job_id>/control` sends a single control command
- `POST /api/jobs/<job_id>/logs` pushes sample log lines

## Run The Web UI

Start the gRPC backend first:

```bash
cd job-orchestrator-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash ./generate.sh
python3 -m server.main
```

Then start the web bridge in a second terminal:

```bash
cd job-orchestrator-service
source .venv/bin/activate
python3 web/app.py
```

Open the browser page at:

```text
http://127.0.0.1:8082
```

If Apache is proxying the web UI under TLS, open:

```text
https://your-hostname/job-orchestrator/
```

Optional environment variables:

```bash
JOB_ORCHESTRATOR_GRPC_ADDR=127.0.0.1:50055 python3 web/app.py
JOB_ORCHESTRATOR_WEB_HOST=0.0.0.0 JOB_ORCHESTRATOR_WEB_PORT=8082 python3 web/app.py
```

## What The Page Does

- Presents a readable service overview similar to an interactive README
- Lets you submit new jobs from the browser
- Fetches current job status on demand
- Streams `WatchJob` updates with SSE
- Sends `PAUSE`, `RESUME`, `CANCEL`, `SET_LOG_LEVEL`, and `GET_STATUS` commands
- Pushes sample log lines through the client-streaming RPC
- Shows ready-to-run `grpcurl` examples for the current backend target

When proxied through Apache on `/job-orchestrator/`, the browser-facing URLs become:

- `GET /job-orchestrator/`
- `GET /job-orchestrator/healthz`
- `GET /job-orchestrator/api/overview`
- `POST /job-orchestrator/api/jobs`