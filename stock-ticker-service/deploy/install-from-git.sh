#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run this script with sudo or as root."
    exit 1
fi

REPO_URL="${1:-https://github.com/prkumar-a11y/gRPC-Applications.git}"
TMPDIR="$(mktemp -d)"

cleanup() {
    rm -rf "${TMPDIR}"
}

trap cleanup EXIT

if ! command -v git >/dev/null 2>&1; then
    echo "git is required to install from a repository URL"
    exit 1
fi

echo "Cloning stock-ticker-service from ${REPO_URL}..."
git clone "${REPO_URL}" "${TMPDIR}"

cd "${TMPDIR}/stock-ticker-service"
chmod +x deploy/install.sh

echo "Installing Stock Ticker gRPC server..."
./deploy/install.sh