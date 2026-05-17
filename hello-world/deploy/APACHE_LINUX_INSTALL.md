# Apache + gRPC Server Installation Guide

This guide covers setting up the Hello World gRPC server on an Apache-based Linux system (CentOS, RHEL, Rocky Linux, Alma Linux, or Fedora).

## Prerequisites

- Apache Linux (CentOS 7+, RHEL 8+, Rocky Linux, Alma Linux, or Fedora)
- Root or sudo access
- Go 1.21+ installed
- 2GB free disk space

## Installation Steps

### Step 1: System Preparation

```bash
# Update system packages
sudo yum update -y

# Install dependencies
sudo yum install -y \
    wget \
    git \
    gcc \
    make \
    systemd-devel

# Verify Go installation
go version

# If Go is not installed, install it
if ! command -v go &> /dev/null; then
    cd /tmp
    wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
    sudo tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
    export PATH=$PATH:/usr/local/go/bin
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
    source ~/.bashrc
    go version
fi
```

### Step 2: Get the Source Code

```bash
# Option 1: Clone from GitHub
cd /tmp
git clone https://github.com/prkumar-a11y/gRPC-Applications.git
cd gRPC-Applications/hello-world

# Option 2: Copy from local machine via SCP
# On your local machine:
scp -r hello-world user@apache-server:/tmp/

# Then on the server:
cd /tmp/hello-world
```

### Step 3: Automated Installation

```bash
# Make script executable
chmod +x deploy/install.sh

# Run installation (requires sudo)
sudo deploy/install.sh

# Script will:
# - Create grpc user
# - Build the server
# - Install systemd service
# - Configure firewall
```

### Step 4: Start and Verify Service

```bash
# Start the service
sudo systemctl start hello-world

# Check status
sudo systemctl status hello-world

# Enable auto-start on boot
sudo systemctl enable hello-world

# View logs
sudo journalctl -u hello-world -f
```

## Manual Step-by-Step Installation (Alternative)

If you prefer manual installation:

### Create System User

```bash
sudo useradd --system --no-create-home --shell /bin/false grpc
```

### Build the Server

```bash
cd /tmp/hello-world
go build -o server ./cmd/server
```

### Install Binary

```bash
# Create installation directory
sudo mkdir -p /opt/hello-world/bin

# Copy binary
sudo cp server /opt/hello-world/bin/
sudo chmod 755 /opt/hello-world/bin/server

# Set ownership
sudo chown -R grpc:grpc /opt/hello-world
```

### Install Systemd Service

```bash
# Copy service file
sudo cp deploy/hello-world.service /etc/systemd/system/

# Set permissions
sudo chmod 644 /etc/systemd/system/hello-world.service

# Reload systemd
sudo systemctl daemon-reload
```

### Configure Firewall

#### For firewalld (RHEL/CentOS 8+, Rocky, Alma):

```bash
# Check if firewalld is running
sudo systemctl status firewalld

# Allow port 50051
sudo firewall-cmd --permanent --add-port=50051/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-all
```

#### For SELinux (if enabled):

```bash
# Check SELinux status
getenforce

# If enforcing, create policy
sudo semanage port -a -t http_port_t -p tcp 50051

# Or disable SELinux for testing
sudo setenforce 0  # Temporary
# Edit /etc/selinux/config for permanent changes
```

### Start Service

```bash
# Start
sudo systemctl start hello-world

# Enable auto-start
sudo systemctl enable hello-world

# Verify running
sudo systemctl status hello-world
```

## Testing the Installation

### Local Test

```bash
# Build the client
go build -o client ./cmd/client

# Test with local server
./client -addr localhost:50051 -name "Apache Server"
```

### Remote Test (from another machine)

```bash
# Get the server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Copy client to your local machine and run
./client -addr $SERVER_IP:50051 -name "Remote Test"
```

### Using grpcurl (alternative testing tool)

```bash
# Install grpcurl
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# Test the service
grpcurl -plaintext -d '{"name":"Apache"}' localhost:50051 helloworld.Greeter/SayHello
```

## Service Management on Apache Linux

### Check Service Status

```bash
sudo systemctl status hello-world

# Detailed status
sudo systemctl show hello-world
```

### View Service Logs

```bash
# Real-time logs
sudo journalctl -u hello-world -f

# Last 50 lines
sudo journalctl -u hello-world -n 50

# Logs from last 1 hour
sudo journalctl -u hello-world --since "1 hour ago"

# Export logs
sudo journalctl -u hello-world > hello-world.log
```

### Restart/Stop Service

```bash
# Restart
sudo systemctl restart hello-world

# Stop
sudo systemctl stop hello-world

# Start again
sudo systemctl start hello-world
```

### Disable Auto-start

```bash
sudo systemctl disable hello-world
```

## Apache Integration (Optional)

### Install Apache Web Server

```bash
# Install Apache
sudo yum install -y httpd

# Enable Apache
sudo systemctl enable httpd
sudo systemctl start httpd
```

### Enable Proxy Modules

```bash
# Enable required modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod http2

# For RHEL/CentOS, edit Apache config directly
sudo sed -i '/LoadModule proxy_module/s/^#//' /etc/httpd/conf.modules.d/00-proxy.conf
```

### Configure Apache Proxy

Create `/etc/httpd/conf.d/grpc-proxy.conf`:

```apache
# Enable HTTP/2
Protocols h2 http/1.1

# Define proxy target
<Location /api/grpc>
    ProxyPass grpc://localhost:50051
    ProxyPassReverse grpc://localhost:50051
    ProxyPreserveHost On
</Location>

# Access logs
ErrorLog /var/log/httpd/grpc-error.log
CustomLog /var/log/httpd/grpc-access.log combined
```

### Restart Apache

```bash
# Test Apache config
sudo apachectl configtest

# Restart Apache
sudo systemctl restart httpd
```

## Troubleshooting for Apache Linux

### Service won't start

```bash
# Check service status with verbose output
sudo systemctl status hello-world -l

# Check system logs
sudo journalctl -xe

# Check if port is already in use
sudo ss -tlnp | grep 50051

# Check binary permissions
ls -la /opt/hello-world/bin/server

# Fix permissions if needed
sudo chown grpc:grpc /opt/hello-world/bin/server
sudo chmod 755 /opt/hello-world/bin/server
```

### SELinux denying access

```bash
# Check SELinux status
getenforce

# Temporarily disable for testing
sudo setenforce 0

# Check audit logs
sudo tail -f /var/log/audit/audit.log | grep denied

# Create custom policy
sudo audit2allow -a -M hello_world
sudo semodule -i hello_world.pp
```

### Firewall blocking connection

```bash
# Verify rule is added
sudo firewall-cmd --list-all | grep 50051

# Add port again
sudo firewall-cmd --permanent --add-port=50051/tcp
sudo firewall-cmd --reload

# Check with netstat
sudo netstat -tlnp | grep 50051
```

### Port already in use

```bash
# Find process using port
sudo lsof -i :50051

# Kill the process
sudo kill -9 <PID>

# Or change the port in service file
sudo systemctl edit hello-world
# Change: ExecStart=/opt/hello-world/bin/server -port=50051
# To:     ExecStart=/opt/hello-world/bin/server -port=9090

sudo systemctl daemon-reload
sudo systemctl restart hello-world
```

### Cannot connect from remote

```bash
# 1. Verify service is listening
sudo netstat -tlnp | grep server
sudo ss -tlnp | grep 50051

# 2. Test local connection
telnet localhost 50051

# 3. Disable firewall temporarily for testing
sudo systemctl stop firewalld

# 4. Test remote connection
# From remote machine: telnet server-ip 50051

# 5. Re-enable firewall with correct rules
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-port=50051/tcp
sudo firewall-cmd --reload
```

## Monitoring and Maintenance

### Monitor Service Health

```bash
# Create monitoring script
cat > /usr/local/bin/check-grpc.sh << 'EOF'
#!/bin/bash
if systemctl is-active --quiet hello-world; then
    echo "gRPC Server: OK"
    systemctl status hello-world --no-pager
else
    echo "gRPC Server: DOWN"
    exit 1
fi
EOF

chmod +x /usr/local/bin/check-grpc.sh

# Run monitoring script
/usr/local/bin/check-grpc.sh
```

### Set Up Log Rotation

Create `/etc/logrotate.d/hello-world`:

```
/var/log/hello-world {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 grpc grpc
    sharedscripts
    postrotate
        systemctl reload hello-world > /dev/null 2>&1 || true
    endscript
}
```

### Monitor Resource Usage

```bash
# Check CPU and memory usage
ps aux | grep hello-world
top -p $(pgrep -f hello-world)

# Monitor network connections
sudo watch -n 1 'netstat -tlnp | grep 50051'
```

## Updating the Application

```bash
# Get latest code
cd /tmp/hello-world
git pull origin main

# Stop service
sudo systemctl stop hello-world

# Rebuild
go build -o server ./cmd/server

# Update binary
sudo cp server /opt/hello-world/bin/
sudo chmod 755 /opt/hello-world/bin/server
sudo chown grpc:grpc /opt/hello-world/bin/server

# Start service
sudo systemctl start hello-world

# Verify
sudo systemctl status hello-world
```

## Production Recommendations

1. **Enable TLS/SSL**
   ```bash
   # Generate self-signed certificate
   sudo openssl req -x509 -newkey rsa:4096 -keyout /opt/hello-world/server.key \
       -out /opt/hello-world/server.crt -days 365 -nodes
   ```

2. **Use SELinux in enforcing mode**
   ```bash
   sudo setenforce 1
   ```

3. **Enable firewall rules**
   ```bash
   sudo firewall-cmd --permanent --add-port=50051/tcp
   sudo firewall-cmd --reload
   ```

4. **Monitor logs regularly**
   ```bash
   sudo journalctl -u hello-world -f
   ```

5. **Keep system updated**
   ```bash
   sudo yum update -y
   go get -u ./...
   ```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop hello-world
sudo systemctl disable hello-world

# Remove service file
sudo rm /etc/systemd/system/hello-world.service
sudo systemctl daemon-reload

# Remove installation directory
sudo rm -rf /opt/hello-world

# Remove firewall rule
sudo firewall-cmd --permanent --remove-port=50051/tcp
sudo firewall-cmd --reload

# Remove user (optional)
sudo userdel grpc
```

## Support and Debugging

For more detailed information:
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for general deployment info
- Review [README.md](../README.md) for API documentation
- Check application logs: `sudo journalctl -u hello-world -f`
- Run diagnostic commands from troubleshooting section above

## Quick Reference Commands

```bash
# Service Control
sudo systemctl start hello-world      # Start service
sudo systemctl stop hello-world       # Stop service
sudo systemctl restart hello-world    # Restart service
sudo systemctl status hello-world     # Check status

# Logs
sudo journalctl -u hello-world -f     # Follow logs
sudo journalctl -u hello-world -n 50  # Last 50 lines

# Testing
go run ./cmd/client/main.go -name "Test"     # Test locally
grpcurl -plaintext -d '{"name":"Test"}' localhost:50051 helloworld.Greeter/SayHello

# Firewall
sudo firewall-cmd --list-all          # List rules
sudo firewall-cmd --permanent --add-port=50051/tcp  # Add port
sudo firewall-cmd --reload            # Reload rules
```

That's it! Your gRPC server is now running on Apache Linux.
