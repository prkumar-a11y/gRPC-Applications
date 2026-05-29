#!/usr/bin/env bash

set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
elif command -v python >/dev/null 2>&1; then
    python_bin="python"
else
    echo "Python is required to generate protobuf files" >&2
    exit 1
fi

"${python_bin}" -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=. \
    --grpc_python_out=. \
    proto/stock_ticker.proto

echo "Protocol buffer files generated successfully!"