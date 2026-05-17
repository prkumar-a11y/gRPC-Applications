# Hello World gRPC - Linux Deployment Guide

This guide covers deploying the Hello World gRPC server on a Linux system.

## Prerequisites

- Go 1.21+ installed on the Linux server
- Root or sudo access
- Port 50051 available (or configured in the systemd service file)

## Quick Installation (Recommended)

### Step 1: Prepare the system

```bash
# Update package manager
sudo apt-get update
sudo apt-get upgrade -y

# Install Go (if not already installed)
sudo apt-get install -y golang-go

# Verify Go installation
go version
```

### Step 2: Clone or copy the project

```bash
# Copy the hello-world directory to your server
# Option A: Using git
git clone https://github.com/prkumar-a11y/gRPC-Applications.git
cd gRPC-Applications/hello-world

# Option B: Copy via SCP
scp -r hello-world user@server:/home/user/
ssh user@server
cd hello-world
```

### Step 3: Run the installation script

```bash
# Make the script executable
chmod +x deploy/install.sh

# Run the installation script (requires sudo)
sudo deploy/install.sh
```

The script will:
- Create a `grpc` system user
- Build the gRPC server binary
- Install the systemd service file
- Configure firewall rules (if firewalld is active)
- Set up proper permissions

### Step 4: Start the service

```bash
# Start the service
sudo systemctl start hello-world

# Verify it's running
sudo systemctl status hello-world

# View logs
sudo journalctl -u hello-world -f
```

### Step 5: Enable auto-start

```bash
# Enable the service to start on boot
sudo systemctl enable hello-world
```

## Manual Installation

If you prefer to install manually or the script doesn't work for your setup:

### Step 1: Create user and directories

```bash
sudo useradd --system --no-create-home --shell /bin/false grpc
sudo mkdir -p /opt/hello-world/bin
```

### Step 2: Build the server

```bash
cd /path/to/hello-world
go build -o /opt/hello-world/bin/server ./cmd/server
sudo chmod +x /opt/hello-world/bin/server
```

### Step 3: Install systemd service

```bash
sudo cp deploy/hello-world.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/hello-world.service
sudo chown -R grpc:grpc /opt/hello-world
sudo systemctl daemon-reload
```

### Step 4: Configure firewall

```bash
# For firewalld
sudo firewall-cmd --permanent --add-port=50051/tcp
sudo firewall-cmd --reload

# For ufw
sudo ufw allow 50051/tcp

# For iptables
sudo iptables -A INPUT -p tcp --dport 50051 -j ACCEPT
```

### Step 5: Start the service

```bash
sudo systemctl start hello-world
sudo systemctl enable hello-world
```
The installed service runs TLS by default and uses generated certs stored in `/opt/hello-world/certs`.
## Testing the Deployment

### Test locally on the server

```bash
# Build the client
go build -o /tmp/client ./cmd/client

# Run the client
/tmp/client -addr localhost:50051 -name "World"
```

### Test from a remote machine

```bash
# Build the client on your development machine
go build -o client ./cmd/client

# Connect to remote server
./client -addr 192.168.1.100:50051 -name "World"
# Replace 192.168.1.100 with your server's IP address
```

## Service Management

### Check service status

```bash
sudo systemctl status hello-world
```

### View real-time logs

```bash
sudo journalctl -u hello-world -f
```

### View recent logs

```bash
sudo journalctl -u hello-world --lines 50
```

### Restart the service

```bash
sudo systemctl restart hello-world
```

### Stop the service

```bash
sudo systemctl stop hello-world
```

### Disable auto-start

```bash
sudo systemctl disable hello-world
```

## Configuration

### Change the listening port

Edit `/etc/systemd/system/hello-world.service` and change:

```
ExecStart=/opt/hello-world/bin/server -port=50051
```

to:

```
ExecStart=/opt/hello-world/bin/server -port=9090
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart hello-world
```

### Change working directory

Edit `/etc/systemd/system/hello-world.service`:

```
WorkingDirectory=/opt/hello-world
```

### Run as different user

Edit `/etc/systemd/system/hello-world.service`:

```
User=myuser
```

## Troubleshooting

### Service won't start

1. Check for errors:
   ```bash
   sudo systemctl status hello-world
   sudo journalctl -u hello-world -n 50
   ```

2. Verify the binary exists:
   ```bash
   ls -la /opt/hello-world/bin/server
   ```

3. Check permissions:
   ```bash
   sudo chown -R grpc:grpc /opt/hello-world
   ```

### Port already in use

```bash
# Check what's using port 50051
sudo lsof -i :50051

# Change the port in the service file or kill the conflicting process
sudo kill -9 <PID>
```

### Permission denied

```bash
# Make sure the binary has execute permissions
sudo chmod +x /opt/hello-world/bin/server

# Make sure grpc user owns the files
sudo chown -R grpc:grpc /opt/hello-world
```

### Cannot connect from remote

1. Check if the service is listening:
   ```bash
   sudo netstat -tlnp | grep 50051
   ```

2. Test local connection:
   ```bash
   telnet localhost 50051
   ```

3. Check firewall:
   ```bash
   sudo firewall-cmd --list-all
   sudo ufw status
   ```

## Updating the Application

### Update the source code

```bash
cd /path/to/hello-world
git pull origin main
# or
cp new-version-files .
```

### Rebuild and redeploy

```bash
# Stop the service
sudo systemctl stop hello-world

# Rebuild
go build -o /opt/hello-world/bin/server ./cmd/server

# Set permissions
sudo chmod +x /opt/hello-world/bin/server
sudo chown grpc:grpc /opt/hello-world/bin/server

# Start the service
sudo systemctl start hello-world

# Verify
sudo systemctl status hello-world
```

## Production Recommendations

### 1. Use systemd socket activation (optional)

Create `/etc/systemd/system/hello-world.socket`:

```ini
[Unit]
Description=Hello World gRPC Socket
Before=hello-world.service

[Socket]
ListenStream=50051
Accept=no

[Install]
WantedBy=sockets.target
```

### 2. Set resource limits

Edit `/etc/systemd/system/hello-world.service`:

```ini
[Service]
LimitNOFILE=65535
LimitNPROC=512
```

### 3. Add health checks

Create a simple monitoring script `/usr/local/bin/check-grpc.sh`:

```bash
#!/bin/bash
if systemctl is-active --quiet hello-world; then
    exit 0
else
    exit 1
fi
```

### 4. Set up log rotation

Create `/etc/logrotate.d/hello-world`:

```
/var/log/hello-world.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 grpc grpc
    sharedscripts
}
```

### 5. Monitor with systemd journal

```bash
# View recent logs
sudo journalctl -u hello-world -n 100

# Follow logs in real-time
sudo journalctl -u hello-world -f

# View since specific time
sudo journalctl -u hello-world --since "2 hours ago"
```

## Uninstallation

To remove the gRPC server:

```bash
# Stop the service
sudo systemctl stop hello-world
sudo systemctl disable hello-world

# Remove systemd service file
sudo rm /etc/systemd/system/hello-world.service
sudo systemctl daemon-reload

# Remove installation directory (optional)
sudo rm -rf /opt/hello-world

# Remove firewall rule (optional)
sudo firewall-cmd --permanent --remove-port=50051/tcp
sudo firewall-cmd --reload

# Remove user (optional)
sudo userdel grpc
```

## Apache Integration (Optional)

To integrate with Apache web server, you can set up a reverse proxy:

### Install Apache modules

```bash
sudo apt-get install -y apache2 libapache2-mod-proxy-html
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
```

### Create Apache configuration

Create `/etc/apache2/sites-available/grpc-proxy.conf`:

```apache
<VirtualHost *:80>
    ServerName grpc.example.com
    
    # Enable proxy modules
    ProxyPreserveHost On
    ProxyPass /api http://localhost:50051
    ProxyPassReverse /api http://localhost:50051
    
    # gRPC requires HTTP/2
    Protocols h2 http/1.1
    
    ErrorLog ${APACHE_LOG_DIR}/grpc-error.log
    CustomLog ${APACHE_LOG_DIR}/grpc-access.log combined
</VirtualHost>
```

### Enable the site

```bash
sudo a2ensite grpc-proxy
sudo systemctl reload apache2
```

## Next Steps

- Read the [README.md](../README.md) for API documentation
- Check [client examples](../cmd/client/main.go)
- Review [systemd service file](hello-world.service)
- Configure SSL/TLS for production use

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u hello-world -f`
2. Review troubleshooting section above
3. Check GitHub issues or documentation
