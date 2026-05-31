# Job Orchestrator gRPC - Linux Deployment Guide

This guide installs the Python job orchestrator gRPC server on Ubuntu-style Linux hosts and runs it as a `systemd` service.

## Prerequisites

- Ubuntu or another `apt`-based Linux distribution
- `sudo` access
- Port `50055/tcp` reachable from the clients that need access

## Quick Install From Git

```bash
git clone https://github.com/prkumar-a11y/gRPC-Applications.git
cd gRPC-Applications/job-orchestrator-service
chmod +x deploy/install.sh
sudo ./deploy/install.sh
```

Or install directly with the helper:

```bash
curl -fsSL https://raw.githubusercontent.com/prkumar-a11y/gRPC-Applications/main/job-orchestrator-service/deploy/install-from-git.sh -o install-job-orchestrator.sh
chmod +x install-job-orchestrator.sh
sudo ./install-job-orchestrator.sh
```

## What The Installer Does

- Creates a dedicated `grpc` system user if needed
- Installs `python3`, `python3-venv`, and `python3-pip`
- Copies the service into `/opt/job-orchestrator-service`
- Creates a virtual environment and installs Python dependencies
- Regenerates Python gRPC stubs from `proto/job_orchestrator.proto`
- Installs `systemd` units named `job-orchestrator` and `job-orchestrator-web`

## Service Commands

```bash
sudo systemctl start job-orchestrator
sudo systemctl enable job-orchestrator
sudo systemctl start job-orchestrator-web
sudo systemctl enable job-orchestrator-web
sudo systemctl status job-orchestrator
sudo systemctl status job-orchestrator-web
sudo journalctl -u job-orchestrator -f
```

By default, the installed service binds to `127.0.0.1:50055` so it can sit safely behind Apache on `443`.
The installed web bridge binds to `127.0.0.1:8082` by default and serves the browser page plus `/api/*` endpoints.

To override the bind address or port without editing the unit file:

```bash
sudo systemctl edit job-orchestrator
```

Then add:

```ini
[Service]
Environment=JOB_ORCHESTRATOR_HOST=0.0.0.0
Environment=JOB_ORCHESTRATOR_PORT=50055
```

Apply the change:

```bash
sudo systemctl daemon-reload
sudo systemctl restart job-orchestrator
```

## Verify The Port

```bash
sudo ss -ltnp | grep 50055
```

## Verify With grpcurl

Install `grpcurl` if needed, then run:

```bash
grpcurl -plaintext localhost:50055 list
grpcurl -plaintext -d '{"name":"smoke-tests","params":{"env":"qa"}}' localhost:50055 joborchestrator.JobOrchestrator/SubmitJob
```

## Apache On 443

Enable the required modules:

```bash
sudo a2enmod ssl proxy proxy_http2 headers
sudo systemctl restart apache2
```

Install the sample vhost from `deploy/apache-job-orchestrator-443.conf` into your Apache site configuration, then update `ServerName` and certificate paths.

Example install steps on Ubuntu:

```bash
sudo cp deploy/apache-job-orchestrator-443.conf /etc/apache2/sites-available/job-orchestrator.conf
sudoedit /etc/apache2/sites-available/job-orchestrator.conf
sudo a2ensite job-orchestrator.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

After Apache is reloaded and both `job-orchestrator` and `job-orchestrator-web` are running, open:

```text
https://your-hostname/job-orchestrator/
```

Then test externally with:

```bash
curl -k https://your-hostname/job-orchestrator/healthz
grpcurl your-hostname:443 list
grpcurl -d '{"name":"smoke-tests","params":{"env":"qa"}}' your-hostname:443 joborchestrator.JobOrchestrator/SubmitJob
```

If you use a self-signed certificate, add `-insecure` to `grpcurl`.

## Direct Remote Access

If you are not using Apache on `443`, change the systemd host override to `0.0.0.0`, restart the service, open `50055/tcp`, and connect directly to the server IP:

```bash
grpcurl -plaintext 198.18.76.38:50055 list
```

## Troubleshooting

If the service does not start:

```bash
sudo systemctl status job-orchestrator
sudo systemctl status job-orchestrator-web
sudo journalctl -u job-orchestrator -n 100 --no-pager
sudo journalctl -u job-orchestrator-web -n 100 --no-pager
```

If protobuf generation fails during install:

```bash
cd /opt/job-orchestrator-service
sudo ./venv/bin/pip install -r requirements.txt
sudo ./venv/bin/python -m grpc_tools.protoc -Iproto --python_out=generated --grpc_python_out=generated proto/job_orchestrator.proto
sudo sed -i 's/^import job_orchestrator_pb2 as /from . import job_orchestrator_pb2 as /' generated/job_orchestrator_pb2_grpc.py
```