#!/usr/bin/env bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo or as root."
  exit 1
fi

REPO_URL="${1:-https://github.com/prkumar-a11y/gRPC-Applications.git}"
TMPDIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "Cloning Hello World from $REPO_URL..."
git clone "$REPO_URL" "$TMPDIR"

cd "$TMPDIR/hello-world"
chmod +x deploy/install.sh

echo "Installing Hello World gRPC server..."
./deploy/install.sh
