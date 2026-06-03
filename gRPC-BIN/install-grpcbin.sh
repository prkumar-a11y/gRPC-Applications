#!/usr/bin/env bash

set -euo pipefail

VERSION="${VERSION:-v1.0.8}"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/grpcbin}"
SERVICE_NAME="${SERVICE_NAME:-grpcbin}"
RUN_USER="${RUN_USER:-grpc}"
RUN_GROUP="${RUN_GROUP:-grpc}"
INSECURE_ADDR="${INSECURE_ADDR:-127.0.0.1:50054}"
SECURE_ADDR="${SECURE_ADDR:-127.0.0.1:50056}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command go
require_command openssl
require_command install
require_command systemctl

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if ! getent group "$RUN_GROUP" >/dev/null 2>&1; then
  groupadd --system "$RUN_GROUP"
fi

if ! id -u "$RUN_USER" >/dev/null 2>&1; then
  useradd --system --gid "$RUN_GROUP" --home-dir "$INSTALL_ROOT" --shell /usr/sbin/nologin "$RUN_USER"
fi

mkdir -p "$INSTALL_ROOT/bin" "$INSTALL_ROOT/cert"

tmp_gobin="$(mktemp -d)"
trap 'rm -rf "$tmp_gobin"' EXIT

GOBIN="$tmp_gobin" go install github.com/moul/grpcbin@"$VERSION"
install -m 0755 "$tmp_gobin/grpcbin" "$INSTALL_ROOT/bin/grpcbin"

if [[ ! -f "$INSTALL_ROOT/cert/server.crt" || ! -f "$INSTALL_ROOT/cert/server.key" ]]; then
  openssl req \
    -x509 \
    -newkey rsa:2048 \
    -sha256 \
    -nodes \
    -days 825 \
    -keyout "$INSTALL_ROOT/cert/server.key" \
    -out "$INSTALL_ROOT/cert/server.crt" \
    -subj "/CN=grpcbin.local" \
    -addext "subjectAltName=DNS:grpcbin.local,IP:127.0.0.1"
fi

chmod 600 "$INSTALL_ROOT/cert/server.key"
chmod 644 "$INSTALL_ROOT/cert/server.crt"
chown -R "$RUN_USER:$RUN_GROUP" "$INSTALL_ROOT"

install -m 0644 "$(dirname "$0")/grpcbin.service" "/etc/systemd/system/$SERVICE_NAME.service"

sed -i \
  -e "s|/opt/grpcbin|$INSTALL_ROOT|g" \
  -e "s|User=grpc|User=$RUN_USER|" \
  -e "s|Group=grpc|Group=$RUN_GROUP|" \
  -e "s|127.0.0.1:50054|$INSECURE_ADDR|" \
  -e "s|127.0.0.1:50056|$SECURE_ADDR|" \
  "/etc/systemd/system/$SERVICE_NAME.service"

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo "grpcbin installed"
echo "  binary:  $INSTALL_ROOT/bin/grpcbin"
echo "  h2c:     $INSECURE_ADDR"
echo "  tls:     $SECURE_ADDR"
echo "  service: $SERVICE_NAME"