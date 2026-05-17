#!/bin/bash
# Installation script for Hello World gRPC Server on Linux

set -e

echo "================================"
echo "Hello World gRPC Installation"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Error: This script must be run as root"
   exit 1
fi

# Configuration
INSTALL_DIR="/opt/hello-world"
SERVICE_USER="grpc"
SERVICE_NAME="hello-world"
PORT=50051

echo "[1/5] Creating user and directories..."
# Create grpc user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
    echo "  ✓ Created $SERVICE_USER user"
else
    echo "  ✓ User $SERVICE_USER already exists"
fi

# Create installation directory
mkdir -p "$INSTALL_DIR/bin"
chmod 755 "$INSTALL_DIR"
echo "  ✓ Created $INSTALL_DIR"

echo ""
echo "[2/5] Building gRPC server..."
# Build the server
cd "$(dirname "$0")/.."
go build -o "$INSTALL_DIR/bin/server" ./cmd/server
chmod +x "$INSTALL_DIR/bin/server"
echo "  ✓ Server built successfully"

echo ""
echo "[3/5] Setting up systemd service..."
# Copy systemd service file
cp "$(dirname "$0")/hello-world.service" "/etc/systemd/system/$SERVICE_NAME.service"
chmod 644 "/etc/systemd/system/$SERVICE_NAME.service"

# Set proper ownership
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
echo "  ✓ Service file installed at /etc/systemd/system/$SERVICE_NAME.service"

echo ""
echo "[4/5] Configuring firewall..."
# Allow port if firewalld is running
if command -v firewall-cmd &> /dev/null && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=$PORT/tcp
    firewall-cmd --reload
    echo "  ✓ Firewall rule added for port $PORT"
else
    echo "  ℹ firewalld not detected, skipping firewall configuration"
    echo "    Make sure port $PORT is open on your firewall"
fi

echo ""
echo "[5/5] Finalizing installation..."
# Reload systemd daemon
systemctl daemon-reload
echo "  ✓ Systemd daemon reloaded"

echo ""
echo "================================"
echo "Installation Complete!"
echo "================================"
echo ""
echo "Quick Start:"
echo "  Start service:   systemctl start $SERVICE_NAME"
echo "  Stop service:    systemctl stop $SERVICE_NAME"
echo "  Restart service: systemctl restart $SERVICE_NAME"
echo "  View logs:       journalctl -u $SERVICE_NAME -f"
echo "  Enable on boot:  systemctl enable $SERVICE_NAME"
echo ""
echo "Service Details:"
echo "  Installation Dir: $INSTALL_DIR"
echo "  Service User:     $SERVICE_USER"
echo "  Listen Port:      $PORT"
echo "  Service File:     /etc/systemd/system/$SERVICE_NAME.service"
echo ""
echo "To start the service run:"
echo "  sudo systemctl start hello-world"
echo ""
