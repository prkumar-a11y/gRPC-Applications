#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Error: this script must be run as root"
    exit 1
fi

INSTALL_DIR="/opt/stock-ticker-service"
SERVICE_USER="grpc"
SERVICE_NAME="stock-ticker"
PORT="50053"
APP_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "================================"
echo "Stock Ticker Installation"
echo "================================"

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd --system --home-dir "${INSTALL_DIR}" --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
    echo "Created ${SERVICE_USER} user"
else
    echo "User ${SERVICE_USER} already exists"
fi

if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip
else
    echo "Error: apt-get is required by this installer"
    exit 1
fi

mkdir -p "${INSTALL_DIR}"
rm -rf "${INSTALL_DIR}/app"
mkdir -p "${INSTALL_DIR}/app"

cp -R "${APP_SOURCE_DIR}/." "${INSTALL_DIR}/app/"
cp "${APP_SOURCE_DIR}/main.py" "${INSTALL_DIR}/main.py"
cp -R "${APP_SOURCE_DIR}/proto" "${INSTALL_DIR}/proto"
cp "${APP_SOURCE_DIR}/requirements.txt" "${INSTALL_DIR}/requirements.txt"
cp "${APP_SOURCE_DIR}/generate.sh" "${INSTALL_DIR}/generate.sh"

python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

chmod +x "${INSTALL_DIR}/generate.sh"
(cd "${INSTALL_DIR}" && "${INSTALL_DIR}/venv/bin/python" -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=. \
    --grpc_python_out=. \
    proto/stock_ticker.proto)

cp "${APP_SOURCE_DIR}/deploy/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
chmod 644 "/etc/systemd/system/${SERVICE_NAME}.service"

if command -v ufw >/dev/null 2>&1; then
    ufw allow "${PORT}/tcp" || true
fi

if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port="${PORT}/tcp"
    firewall-cmd --reload
fi

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"
systemctl daemon-reload

echo ""
echo "Installation complete"
echo "Start service:   systemctl start ${SERVICE_NAME}"
echo "Enable service:  systemctl enable ${SERVICE_NAME}"
echo "View logs:       journalctl -u ${SERVICE_NAME} -f"
echo "Listen port:     ${PORT}"