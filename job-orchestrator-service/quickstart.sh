#!/bin/bash
# Quick start script for Job Orchestrator service

set -e

echo "Job Orchestrator Service - Quick Start"
echo "======================================="
echo ""

# Check if in correct directory
if [ ! -f "proto/job_orchestrator.proto" ]; then
    echo "Error: Please run this script from the job-orchestrator-service directory"
    exit 1
fi

# Install dependencies
echo "1. Installing dependencies..."
pip install -q -r requirements.txt

# Generate gRPC code
echo "2. Generating gRPC code..."
./generate.sh

# Start server in background
echo "3. Starting gRPC server..."
python -m server.main &
SERVER_PID=$!

# Wait for server to start
echo "4. Waiting for server to be ready..."
sleep 3

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "   ✗ Server failed to start"
    exit 1
fi

echo "   ✓ Server is running (PID: $SERVER_PID)"
echo ""
echo "======================================="
echo "Server is ready on localhost:50055"
echo ""
echo "Try these commands:"
echo ""
echo "  # Submit a job"
echo "  python -m client.cli submit --name smoke-tests --param env=qa"
echo ""
echo "  # Watch a job (replace <job-id>)"
echo "  python -m client.cli watch --job-id <job-id>"
echo ""
echo "  # Interactive shell"
echo "  python -m client.cli shell --job-id <job-id>"
echo ""
echo "  # Launch TUI"
echo "  python -m client.tui_app"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================="
echo ""

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping server...'; kill $SERVER_PID 2>/dev/null; exit 0" INT
wait $SERVER_PID
