# Hello World gRPC Application

A simple, production-ready Hello World gRPC service demonstrating unary RPC calls in Go.

## Features

- **Simple Unary RPC**: Single request-response pattern
- **Production Ready**: Includes systemd service, Docker support, and deployment scripts
- **Easy Testing**: Built-in client for testing the server
- **Linux Deployment**: Complete deployment guide for Apache/Linux systems
- **Docker Support**: Containerized deployment option

## Quick Start

### Local Development

```bash
# Build
make build

# Terminal 1: Start server
make run-server

# Terminal 2: Run client
make run-client
```

### Using Docker

```bash
# Build and run with docker-compose
cd deploy
docker-compose up

# In another terminal, test the service
docker run --rm --network host \
  --entrypoint /bin/sh \
  hello-world_grpc-server:latest -c "wget http://localhost:50051"
```

### Install from Git on Linux

```bash
git clone https://github.com/prkumar-a11y/gRPC-Applications.git
cd gRPC-Applications/hello-world
chmod +x deploy/install.sh
sudo deploy/install.sh
```

The installation script will build the server, install a systemd service, and open port `50051` if `firewalld` is enabled.

## Architecture

```
hello-world/
├── proto/
│   └── helloworld.proto          # Protocol buffer definitions
├── pkg/
│   ├── helloworld.pb.go          # Generated protobuf code
│   └── helloworld_grpc.pb.go     # Generated gRPC code
├── cmd/
│   ├── server/main.go            # Server implementation
│   └── client/main.go            # Client implementation
├── deploy/
│   ├── install.sh                # Linux installation script
│   ├── hello-world.service       # Systemd service file
│   ├── Dockerfile                # Docker build file
│   ├── docker-compose.yml        # Docker compose configuration
│   └── DEPLOYMENT.md             # Detailed deployment guide
├── go.mod                        # Go modules
├── Makefile                      # Build tasks
└── README.md                     # This file
```

## API

### Service: Greeter

#### RPC: SayHello
Unary RPC that sends a greeting message.

**Request: HelloRequest**
```protobuf
message HelloRequest {
  string name = 1;
}
```

**Response: HelloReply**
```protobuf
message HelloReply {
  string message = 1;
}
```

**Example:**
```
Request:  {name: "World"}
Response: {message: "Hello World"}
```

## Usage

### Server

```bash
# Run with default port (50051)
go run ./cmd/server/main.go

# Run with custom port
go run ./cmd/server/main.go -port=9090

# Run with TLS enabled
# Assumes certificate and key files are present
go run ./cmd/server/main.go -tls -cert=server.crt -key=server.key
```

### Client

```bash
# Connect to local server
go run ./cmd/client/main.go -name "World"

# Connect to remote server
go run ./cmd/client/main.go -addr "192.168.1.100:50051" -name "World"

# Connect to a TLS server using a custom CA certificate
go run ./cmd/client/main.go -tls -ca_cert=cert.pem -addr "localhost:50051" -name "World"

# Connect to a TLS server using system CA trust
go run ./cmd/client/main.go -tls -addr "localhost:50051" -name "World"
```

## Linux Deployment

See [DEPLOYMENT.md](deploy/DEPLOYMENT.md) for comprehensive deployment instructions.

### Quick Installation

```bash
# Make installation script executable
chmod +x deploy/install.sh

# Run installation (requires sudo)
sudo deploy/install.sh

# The installed service uses TLS and stores generated certs in /opt/hello-world/certs

# Start service
sudo systemctl start hello-world

# Check status
sudo systemctl status hello-world
```

### Service Management

```bash
# Start
sudo systemctl start hello-world

# Stop
sudo systemctl stop hello-world

# Restart
sudo systemctl restart hello-world

# Enable auto-start on boot
sudo systemctl enable hello-world

# View logs
sudo journalctl -u hello-world -f
```

## Docker Deployment

### Build Docker image

```bash
cd deploy
docker build -t hello-world-grpc .
```

### Run container

```bash
# Run in foreground
docker run -p 50051:50051 hello-world-grpc

# Run in background
docker run -d -p 50051:50051 --name grpc-server hello-world-grpc

# View logs
docker logs -f grpc-server

# Stop container
docker stop grpc-server
```

### Using Docker Compose

```bash
cd deploy

# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Testing

### Local test

```bash
make test
```

This will:
1. Build the server and client
2. Start the server in background
3. Run the client
4. Stop the server

### Manual testing

```bash
# Terminal 1: Start server
go run ./cmd/server/main.go

# Terminal 2: Run client
go run ./cmd/client/main.go -name "Alice"
go run ./cmd/client/main.go -name "Bob"
```

### Remote testing

```bash
# From another machine
go run ./cmd/client/main.go -addr "server-ip:50051" -name "Remote User"
```

## Development

### Regenerate protobuf files

If you modify `proto/helloworld.proto`:

```bash
# Install protoc and protoc-gen-go, protoc-gen-go-grpc if not already installed
# macOS: brew install protobuf protoc-gen-go protoc-gen-go-grpc
# Linux: see deploy/DEPLOYMENT.md

# Generate code
protoc --go_out=pkg --go-grpc_out=pkg proto/helloworld.proto
```

### Build for specific OS/Architecture

```bash
# Linux AMD64
GOOS=linux GOARCH=amd64 go build -o server-linux-amd64 ./cmd/server

# Linux ARM64
GOOS=linux GOARCH=arm64 go build -o server-linux-arm64 ./cmd/server

# Windows
GOOS=windows GOARCH=amd64 go build -o server-windows-amd64.exe ./cmd/server

# macOS
GOOS=darwin GOARCH=amd64 go build -o server-darwin-amd64 ./cmd/server
```

## Monitoring

### View service logs

```bash
# Last 100 lines
sudo journalctl -u hello-world -n 100

# Follow in real-time
sudo journalctl -u hello-world -f

# Last 2 hours
sudo journalctl -u hello-world --since "2 hours ago"
```

### Check service status

```bash
sudo systemctl status hello-world
```

### Monitor process

```bash
# Show process info
ps aux | grep server

# Show network connections
netstat -tlnp | grep 50051
sudo ss -tlnp | grep 50051
```

## Troubleshooting

### Port already in use

```bash
# Find process using port 50051
sudo lsof -i :50051
sudo ss -tlnp | grep :50051

# Kill the process (be careful!)
sudo kill -9 <PID>

# Or use a different port
go run ./cmd/server/main.go -port=9090
```

### Service won't start

1. Check logs:
   ```bash
   sudo journalctl -u hello-world -n 50
   ```

2. Verify binary exists:
   ```bash
   ls -la /opt/hello-world/bin/server
   ```

3. Check permissions:
   ```bash
   sudo chown -R grpc:grpc /opt/hello-world
   ```

### Connection refused

1. Verify server is running:
   ```bash
   sudo systemctl status hello-world
   ```

2. Check firewall:
   ```bash
   sudo firewall-cmd --list-all
   sudo ufw status
   ```

3. Test local connection:
   ```bash
   telnet localhost 50051
   ```

### Build errors

```bash
# Download dependencies
go mod download
go mod tidy

# Clean build cache
go clean -cache
go clean -modcache

# Rebuild
go build -o bin/server ./cmd/server
```

## Configuration

### Change port

Edit `deploy/hello-world.service`:

```ini
ExecStart=/opt/hello-world/bin/server -port=9090
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart hello-world
```

### Change service user

Edit `deploy/hello-world.service`:

```ini
User=myuser
```

Create the user first:

```bash
sudo useradd --system --no-create-home --shell /bin/false myuser
sudo chown -R myuser:myuser /opt/hello-world
sudo systemctl daemon-reload
sudo systemctl restart hello-world
```

## Performance

### Benchmarking

```bash
# Build in release mode
go build -o bin/server -ldflags="-s -w" ./cmd/server

# Simple load test using grpcurl
grpcurl -plaintext -d '{"name":"test"}' localhost:50051 helloworld.Greeter/SayHello

# Multiple requests
for i in {1..1000}; do
  grpcurl -plaintext -d "{\"name\":\"user$i\"}" localhost:50051 helloworld.Greeter/SayHello
done
```

## Security Considerations

### For Production:

1. **Enable TLS/SSL**
   ```bash
   # Generate certificates
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   
   # Run the server with TLS enabled
   go run ./cmd/server/main.go -tls -cert=cert.pem -key=key.pem
   
   # Run the client with a custom CA cert
   go run ./cmd/client/main.go -tls -ca_cert=cert.pem -addr "localhost:50051" -name "World"
   ```

2. **Use firewall rules**
   ```bash
   sudo firewall-cmd --permanent --add-port=50051/tcp
   sudo firewall-cmd --reload
   ```

3. **Run as non-root user** (default in systemd service)

4. **Keep dependencies updated**
   ```bash
   go get -u ./...
   ```

5. **Monitor logs regularly**
   ```bash
   sudo journalctl -u hello-world -f
   ```

## License

MIT

## Contributing

Feel free to submit issues and pull requests.

## Support

For detailed deployment instructions, see [DEPLOYMENT.md](deploy/DEPLOYMENT.md)

For more information about gRPC, visit [grpc.io](https://grpc.io)
