#!/bin/bash

# Generate gRPC code from proto files

PROTO_DIR="proto"
OUT_DIR="generated"

# Create output directory
mkdir -p "$OUT_DIR"

# Generate Python code
python -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "$PROTO_DIR/job_orchestrator.proto"

echo "✓ Generated gRPC code in $OUT_DIR/"

# Fix imports in generated files (grpcio generates relative imports)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/import job_orchestrator_pb2/from . import job_orchestrator_pb2/' "$OUT_DIR/job_orchestrator_pb2_grpc.py"
else
    # Linux
    sed -i 's/import job_orchestrator_pb2/from . import job_orchestrator_pb2/' "$OUT_DIR/job_orchestrator_pb2_grpc.py"
fi

echo "✓ Fixed imports"
