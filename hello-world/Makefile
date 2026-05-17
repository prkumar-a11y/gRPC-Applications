.PHONY: build build-server build-client run-server run-client clean help

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

# Run client
run-client: build-client
	@echo "Running client..."
	@./bin/client -name "World"

# Test - run server and client
test: build
	@echo "Testing gRPC application..."
	@./bin/server &
	@sleep 1
	@./bin/client -name "gRPC"
	@pkill -f "./bin/server" || true

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@rm -rf bin/
	@echo "✓ Clean complete"

# Help message
help:
	@echo "Hello World gRPC - Makefile Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  build           Build server and client"
	@echo "  build-server    Build server only"
	@echo "  build-client    Build client only"
	@echo "  run-server      Build and run server"
	@echo "  run-client      Build and run client"
	@echo "  test            Run quick test"
	@echo "  clean           Remove build artifacts"
	@echo "  help            Show this help message"
