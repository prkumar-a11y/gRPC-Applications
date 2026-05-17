#!/bin/bash
# Docker deployment script for Hello World gRPC Server

set -e

echo "================================"
echo "Hello World gRPC Docker Setup"
echo "================================"
echo ""

# Configuration
CONTAINER_NAME="hello-world-grpc"
IMAGE_NAME="hello-world-grpc"
PORT=50051

echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker is installed"

echo ""
echo "[1/3] Building Docker image..."
cd "$(dirname "$0")/.."

docker build -f deploy/Dockerfile -t "$IMAGE_NAME" .
echo "✓ Docker image built: $IMAGE_NAME"

echo ""
echo "[2/3] Removing old container (if exists)..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
echo "✓ Clean slate ready"

echo ""
echo "[3/3] Starting container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:$PORT" \
  --restart unless-stopped \
  "$IMAGE_NAME"

echo "✓ Container started"

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Container Details:"
echo "  Name:   $CONTAINER_NAME"
echo "  Image:  $IMAGE_NAME"
echo "  Port:   $PORT"
echo ""
echo "Quick Commands:"
echo "  View logs:      docker logs -f $CONTAINER_NAME"
echo "  Stop:           docker stop $CONTAINER_NAME"
echo "  Start:          docker start $CONTAINER_NAME"
echo "  Remove:         docker rm -f $CONTAINER_NAME"
echo "  Test:           docker exec $CONTAINER_NAME /app/server"
echo ""
echo "Test the service:"
echo "  curl http://localhost:$PORT"
echo ""
