.PHONY: build build-server build-client run-server run-client demo clean help proto-gen

# Build both server and client
build: build-server build-client
	@echo "✓ Build complete"

# Build server
build-server:
	@echo "Building server..."
	@go build -o bin/server ./cmd/server
	@echo "✓ Server built: bin/server"

# Build client
build-client:
	@echo "Building client..."
	@go build -o bin/client ./cmd/client
	@echo "✓ Client built: bin/client"

# Run server
run-server: build-server
	@echo "Starting server on :50051..."
	@./bin/server

# Run client demo
run-client: build-client
	@echo "Running client demo..."
	@./bin/client

# Run full demo (requires tmux or running in separate terminals)
demo: build-server build-client
	@echo "=== Chat Service Demo ==="
	@echo "Starting server in background..."
	@./bin/server &
	@sleep 2
	@echo "Running client demo..."
	@./bin/client
	@pkill -f "./bin/server" || true

# Generate protobuf files
proto-gen:
	@echo "Generating protobuf files..."
	@protoc --go_out=pkg --go-grpc_out=pkg proto/chat.proto
	@echo "✓ Protobuf files generated"

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@rm -rf bin/
	@echo "✓ Clean complete"

# Format code
fmt:
	@echo "Formatting code..."
	@go fmt ./...
	@echo "✓ Format complete"

# Run tests
test:
	@echo "Running tests..."
	@go test ./...

# Install dependencies
deps:
	@echo "Installing dependencies..."
	@go mod download
	@go mod tidy
	@echo "✓ Dependencies installed"

# Help message
help:
	@echo "Chat Service - Makefile Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  build           Build server and client"
	@echo "  build-server    Build server only"
	@echo "  build-client    Build client only"
	@echo "  run-server      Build and run server"
	@echo "  run-client      Build and run client"
	@echo "  demo            Run full demo"
	@echo "  proto-gen       Generate protobuf files from proto/chat.proto"
	@echo "  deps            Download and tidy dependencies"
	@echo "  fmt             Format code"
	@echo "  test            Run tests"
	@echo "  clean           Remove build artifacts"
	@echo "  help            Show this help message"
