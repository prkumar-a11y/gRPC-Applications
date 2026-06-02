#!/usr/bin/env bash

set -euo pipefail

HOSTNAME="${1:-grpc-service-apache-origin.qa.akamai.com}"
CERT_DIR="${2:-/etc/ssl/grpc-services}"
CRT_FILE="$CERT_DIR/$HOSTNAME.crt"
KEY_FILE="$CERT_DIR/$HOSTNAME.key"

mkdir -p "$CERT_DIR"

openssl req \
  -x509 \
  -newkey rsa:4096 \
  -sha256 \
  -nodes \
  -days 825 \
  -keyout "$KEY_FILE" \
  -out "$CRT_FILE" \
  -subj "/CN=$HOSTNAME" \
  -addext "subjectAltName=DNS:$HOSTNAME"

chmod 600 "$KEY_FILE"
chmod 644 "$CRT_FILE"

echo "Created certificate: $CRT_FILE"
echo "Created private key: $KEY_FILE"