#!/bin/bash
# Test script for Job Orchestrator service

echo "Testing Job Orchestrator gRPC Service"
echo "======================================"
echo ""

# Check if server is running
echo "1. Checking if service is available..."
if grpcurl -plaintext localhost:50055 list > /dev/null 2>&1; then
    echo "   ✓ Service is running on localhost:50055"
else
    echo "   ✗ Service is not running. Start it with: make server"
    exit 1
fi

echo ""
echo "2. Listing available services..."
grpcurl -plaintext localhost:50055 list

echo ""
echo "3. Describing JobOrchestrator service..."
grpcurl -plaintext localhost:50055 describe joborchestrator.JobOrchestrator

echo ""
echo "4. Submitting a test job..."
RESULT=$(grpcurl -plaintext -d '{"name":"smoke-tests","params":{"env":"qa","suite":"smoke"}}' \
    localhost:50055 joborchestrator.JobOrchestrator/SubmitJob 2>&1)

echo "$RESULT"

# Extract job ID (simple grep approach)
JOB_ID=$(echo "$RESULT" | grep -o '"job_id": "[^"]*"' | cut -d'"' -f4)

if [ -n "$JOB_ID" ]; then
    echo ""
    echo "5. Getting job status for: $JOB_ID"
    grpcurl -plaintext -d "{\"id\":\"$JOB_ID\"}" \
        localhost:50055 joborchestrator.JobOrchestrator/GetJobStatus
    
    echo ""
    echo "6. Watching job updates (will show first few updates)..."
    echo "   Press Ctrl+C to stop"
    timeout 10 grpcurl -plaintext -d "{\"id\":\"$JOB_ID\"}" \
        localhost:50055 joborchestrator.JobOrchestrator/WatchJob || true
fi

echo ""
echo "======================================"
echo "Test complete!"
echo ""
echo "To test via Envoy proxy:"
echo "  grpcurl -insecure -d '{\"name\":\"test\"}' \\"
echo "    localhost:443 joborchestrator.JobOrchestrator/SubmitJob"
