# Job Orchestrator gRPC Service

A comprehensive demonstration of **all four gRPC communication patterns** using Python with async gRPC (`grpc.aio`), featuring a Terminal User Interface (TUI) for interactive job management.

## 🎯 Purpose

This service showcases:

1. **Unary RPC**: Submit jobs and query status
2. **Client Streaming**: Push log lines from client to server
3. **Server Streaming**: Watch real-time job updates
4. **Bidirectional Streaming**: Interactive job control session

## 📁 Project Structure

```
job-orchestrator-service/
├── proto/
│   └── job_orchestrator.proto       # gRPC service definition
├── server/
│   ├── __init__.py
│   ├── main.py                      # Server entry point
│   ├── service_impl.py              # gRPC servicer implementation
│   ├── models.py                    # Data models
│   └── state_store.py               # In-memory state management
├── client/
│   ├── __init__.py
│   ├── cli.py                       # CLI client (all 4 patterns)
│   └── tui_app.py                   # Full TUI using Textual
├── generated/                       # Auto-generated gRPC code
│   ├── job_orchestrator_pb2.py
│   └── job_orchestrator_pb2_grpc.py
├── requirements.txt                 # Python dependencies
├── Makefile                         # Build and run commands
├── Dockerfile                       # Container image
├── generate.sh                      # Code generation script
└── README.md                        # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or virtualenv

### Installation

1. **Clone and navigate:**
   ```bash
   cd job-orchestrator-service
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   make install
   # or: pip install -r requirements.txt
   ```

4. **Generate gRPC code:**
   ```bash
   make generate
   # or: ./generate.sh
   ```

### Running the Server

```bash
make server
# or: python -m server.main
```

The server starts on `localhost:50055` with gRPC reflection enabled.

## 💻 Client Usage

### CLI Client

The CLI demonstrates all four gRPC patterns:

#### 1. Submit Job (Unary)

```bash
python -m client.cli submit --name smoke-tests --param env=qa --param suite=smoke

# Output:
# ✓ Job submitted successfully!
#   Job ID: a1b2c3d4
#   Message: Job 'smoke-tests' submitted successfully
```

Or using Makefile:
```bash
make cli-submit
```

#### 2. Get Job Status (Unary)

```bash
python -m client.cli status --job-id a1b2c3d4

# Output:
# Job Status for a1b2c3d4:
#   State: RUNNING
#   Message: Processing step 3/10
#   Created: Sun Dec  1 10:30:15 2025
#   Updated: Sun Dec  1 10:30:45 2025
#   Params: {'env': 'qa', 'suite': 'smoke'}
```

Or using Makefile:
```bash
make cli-status JOB_ID=a1b2c3d4
```

#### 3. Push Logs (Client Streaming)

Create a test log file:
```bash
cat > test.log <<EOF
INFO: Starting test suite
DEBUG: Loading configuration
INFO: Running test case 1
ERROR: Test case 2 failed
WARN: Retry attempt 1
INFO: Test completed
EOF
```

Push logs:
```bash
python -m client.cli push-logs --job-id a1b2c3d4 test.log

# Output:
# ✓ Logs pushed successfully!
#   Job ID: a1b2c3d4
#   Total lines: 6
#   Error lines: 1
#   Warning lines: 1
#   Summary: Processed 6 log lines (1 errors, 1 warnings)
```

Or using Makefile:
```bash
make cli-logs JOB_ID=a1b2c3d4 FILE=test.log
```

#### 4. Watch Job Updates (Server Streaming)

```bash
python -m client.cli watch --job-id a1b2c3d4

# Output:
# Watching job a1b2c3d4... (Press Ctrl+C to stop)
# --------------------------------------------------------------------------------
# [Sun Dec  1 10:30:15 2025] PENDING (0%): Current state: Initialized
# [Sun Dec  1 10:30:17 2025] RUNNING (0%): Job started
# [Sun Dec  1 10:30:20 2025] RUNNING (10%): Processing step 1/10
# [Sun Dec  1 10:30:25 2025] RUNNING (20%): Processing step 2/10
# ...
# [Sun Dec  1 10:31:05 2025] COMPLETED (100%): Job completed successfully
# --------------------------------------------------------------------------------
# Job finished with state: COMPLETED
```

Or using Makefile:
```bash
make cli-watch JOB_ID=a1b2c3d4
```

#### 5. Interactive Shell (Bidirectional Streaming)

```bash
python -m client.cli shell --job-id a1b2c3d4

# Output:
# Interactive session for job a1b2c3d4
# Commands: PAUSE, RESUME, CANCEL, SET_LOG_LEVEL <level>, GET_STATUS, quit
# --------------------------------------------------------------------------------
# [Sun Dec  1 10:30:15 2025] [ACK] Interactive session started. Available commands: ...
# > GET_STATUS
# [Sun Dec  1 10:30:16 2025] [STATUS] State: RUNNING, Progress: 30%, Message: Processing step 3/10
# > PAUSE
# [Sun Dec  1 10:30:20 2025] [ACK] Job paused
# > RESUME
# [Sun Dec  1 10:30:25 2025] [ACK] Job resumed
# > SET_LOG_LEVEL DEBUG
# [Sun Dec  1 10:30:30 2025] [ACK] Log level set to DEBUG
# > quit
# --------------------------------------------------------------------------------
# Session closed
```

Or using Makefile:
```bash
make cli-shell JOB_ID=a1b2c3d4
```

### TUI Client (Textual)

**Note:** Make sure dependencies are installed first: `make install`

Launch the full-screen terminal UI:

```bash
make tui
# or: python3 -m client.tui_app
```

**TUI Features:**
- **Jobs Table**: View all jobs with their state and progress
- **Status Panel**: Real-time updates for selected job (server streaming)
- **Logs Panel**: Session events and system messages
- **Command Input**: Type commands to interact with jobs

**TUI Commands:**
- `submit <name> [key=value ...]` - Submit new job
- `watch <job-id>` - Start watching a job
- `status` - Get current job status
- `pause` / `resume` / `cancel` - Control job execution
- `quit` or press `q` - Exit TUI

**Troubleshooting:** If you get `ModuleNotFoundError: No module named 'textual'`, run:
```bash
pip3 install textual==0.47.1 rich==13.7.0
```

## 🔍 gRPC Pattern Demonstrations

### Pattern 1: Unary RPC
**Client sends one request → Server sends one response**

```protobuf
rpc SubmitJob(JobSpec) returns (JobAck);
rpc GetJobStatus(JobId) returns (JobStatus);
```

**Use case**: Simple request-response operations like submitting a job or querying status.

### Pattern 2: Client Streaming
**Client sends stream of messages → Server sends one response**

```protobuf
rpc PushLogs(stream LogLine) returns (LogSummary);
```

**Use case**: Uploading large datasets, log ingestion, batch operations.

### Pattern 3: Server Streaming
**Client sends one request → Server sends stream of responses**

```protobuf
rpc WatchJob(JobId) returns (stream JobUpdate);
```

**Use case**: Real-time updates, progress monitoring, event subscriptions.

### Pattern 4: Bidirectional Streaming
**Client and server exchange streams independently**

```protobuf
rpc InteractiveSession(stream ControlMessage) returns (stream SessionEvent);
```

**Use case**: Interactive sessions, real-time collaboration, bidirectional communication.

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t job-orchestrator:latest .
```

### Run Container

```bash
docker run -p 50055:50055 job-orchestrator:latest
```

### Docker Compose Integration

Add to your existing `docker-compose.yaml`:

```yaml
  job-orchestrator-service:
    build:
      context: ./job-orchestrator-service
      dockerfile: Dockerfile
    networks: [default]
    expose:
      - "50055"
    ports:
      - "50055:50055"
    restart: unless-stopped
```

## 🔧 Development

### Project Dependencies

- **grpcio** (1.60.0): Core gRPC library
- **grpcio-tools**: Protobuf compiler and code generator
- **grpcio-reflection**: Server reflection for tools like `grpcurl`
- **textual** (0.47.1): Modern TUI framework
- **rich** (13.7.0): Terminal formatting and colors

### Regenerate gRPC Code

After modifying `proto/job_orchestrator.proto`:

```bash
make generate
```

This runs `grpc_tools.protoc` to generate:
- `job_orchestrator_pb2.py` (message classes)
- `job_orchestrator_pb2_grpc.py` (service stubs and servicers)

### Code Organization

- **Models** (`server/models.py`): Data classes for Job, LogEntry, JobState enum
- **State Store** (`server/state_store.py`): Thread-safe in-memory storage with pub/sub
- **Service Implementation** (`server/service_impl.py`): All RPC handlers with async/await
- **Server** (`server/main.py`): Server setup, reflection, graceful shutdown

## 🧪 Testing with grpcurl

Install [grpcurl](https://github.com/fullstorydev/grpcurl) to test the service:

```bash
# List services
grpcurl -plaintext localhost:50055 list

# Describe service
grpcurl -plaintext localhost:50055 describe joborchestrator.JobOrchestrator

# Submit a job
grpcurl -plaintext -d '{"name":"test-job","params":{"env":"dev"}}' \
  localhost:50055 joborchestrator.JobOrchestrator/SubmitJob

# Get status
grpcurl -plaintext -d '{"id":"<job-id>"}' \
  localhost:50055 joborchestrator.JobOrchestrator/GetJobStatus

# Watch job (server streaming)
grpcurl -plaintext -d '{"id":"<job-id>"}' \
  localhost:50055 joborchestrator.JobOrchestrator/WatchJob
```

## 📚 Learning Resources

This project demonstrates:

- **Async Python**: Proper use of `asyncio`, `grpc.aio`, concurrent tasks
- **gRPC Patterns**: All four communication patterns in one service
- **State Management**: In-memory pub/sub with async locks
- **Error Handling**: gRPC status codes, cancellation, graceful shutdown
- **TUI Development**: Using Textual for terminal interfaces
- **Service Design**: Clean separation of concerns, type hints, logging

## 🔧 Troubleshooting

### TUI Not Working

**Problem:** `ModuleNotFoundError: No module named 'textual'`

**Solution:**
```bash
cd job-orchestrator-service
pip3 install -r requirements.txt
# or manually:
pip3 install textual==0.47.1 rich==13.7.0
```

**Problem:** TUI connects to wrong port

**Solution:** connection issues:
```bash
# Check if server is running
docker-compose ps | grep job-orchestrator
# or locally:
lsof -i :50055

# Verify with CLI first
python3 -m client.cli submit --name test
```

**Problem:** TUI shows connection errors

**Checklist:**
1. ✅ Server is running: `make server` or `docker-compose up -d`
2. ✅ Dependencies installed: `make install`
3. ✅ Generated code exists: `make generate`
4. ✅ Port 50055 is accessible: `nc -zv localhost 50055`

### Server Won't Start

**Problem:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
# Make sure you're in the service directory
cd job-orchestrator-service

# Regenerate protobuf code
make generate

# Reinstall dependencies
pip3 install -r requirements.txt

# Try running server
make server
```

**Problem:** Port already in use

**Solution:**
```bash
# Find what's using port 50055
lsof -i :50055
# Kill it or change the port in server/main.py
```

### CLI Not Working

**Problem:** `Failed to connect to server`

**Solution:**
```bash
# Check server is running
grpcurl -plaintext localhost:50055 list

# If not running, start it:
make server

# Test with simple command
make cli-submit
```

## 🔗 Integration with Envoy

This service can be integrated with your Envoy proxy setup. Add to `envoy.yaml`:

```yaml
- name: job-orchestrator-service
  connect_timeout: 2s
  type: STRICT_DNS
  http2_protocol_options: {}
  load_assignment:
    cluster_name: job-orchestrator-service
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: job-orchestrator-service
              port_value: 50055
```

Add route:

```yaml
- match:
    prefix: "/joborchestrator.JobOrchestrator/"
  route:
    cluster: job-orchestrator-service
    timeout: 60s
```

## 📝 License

This is a demonstration project for learning gRPC patterns.

## 🤝 Contributing

This project is part of a larger gRPC-Envoy demonstration. See the main repository for contribution guidelines.

---

**Happy gRPC streaming!** 🚀
