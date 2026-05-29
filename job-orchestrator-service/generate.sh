#!/bin/bash

set -euo pipefail

# Generate gRPC code from proto files

PROTO_DIR="proto"
OUT_DIR="generated"

# Create output directory
mkdir -p "$OUT_DIR"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="python3"
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

# Generate Python code
"${PYTHON_BIN}" -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "$PROTO_DIR/job_orchestrator.proto"

echo "✓ Generated gRPC code in $OUT_DIR/"

# Fix imports in generated files (grpcio generates relative imports)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/^import job_orchestrator_pb2 as /from . import job_orchestrator_pb2 as /' "$OUT_DIR/job_orchestrator_pb2_grpc.py"
else
    # Linux
    sed -i 's/^import job_orchestrator_pb2 as /from . import job_orchestrator_pb2 as /' "$OUT_DIR/job_orchestrator_pb2_grpc.py"
fi

echo "✓ Fixed imports"
