# Stock Ticker gRPC - Linux Deployment Guide

This guide installs the Python stock ticker gRPC server on Ubuntu-style Linux hosts such as `Linux a198-18-76-38 5.15.0-134-generic`.

## Prerequisites

- Ubuntu or another `apt`-based Linux distribution
- `sudo` access
- Port `50053/tcp` reachable from clients

## Quick Install From Git

```bash
git clone https://github.com/prkumar-a11y/gRPC-Applications.git
cd gRPC-Applications/stock-ticker-service
chmod +x deploy/install.sh
sudo ./deploy/install.sh
```

Or install directly with the helper:

```bash
curl -fsSL https://raw.githubusercontent.com/prkumar-a11y/gRPC-Applications/main/stock-ticker-service/deploy/install-from-git.sh -o install-stock-ticker.sh
chmod +x install-stock-ticker.sh
sudo ./install-stock-ticker.sh
```

## What The Installer Does

- Creates a dedicated `grpc` system user if needed
- Installs `python3`, `python3-venv`, and `python3-pip`
- Copies the service into `/opt/stock-ticker-service`
- Creates a virtual environment and installs Python dependencies
- Generates Python gRPC stubs from `proto/stock_ticker.proto`
- Installs a `systemd` unit named `stock-ticker`

## Service Commands

```bash
sudo systemctl start stock-ticker
sudo systemctl enable stock-ticker
sudo systemctl status stock-ticker
sudo journalctl -u stock-ticker -f
```

## Verify The Port

```bash
sudo ss -ltnp | grep 50053
```

## Verify Health With grpcurl

Install `grpcurl` if needed, then run:

```bash
grpcurl -plaintext localhost:50053 list
grpcurl -plaintext localhost:50053 stockticker.StockTickerService/GetAvailableSymbols
grpcurl -plaintext -d '{"symbol":"AAPL"}' localhost:50053 stockticker.StockTickerService/GetCurrentPrice
```

## Remote Access

Open `50053/tcp` on the host firewall and connect from your client machine using the server's IP address:

```bash
grpcurl -plaintext 198.18.76.38:50053 list
```

## Troubleshooting

If the service does not start:

```bash
sudo systemctl status stock-ticker
sudo journalctl -u stock-ticker -n 100 --no-pager
```

If protobuf generation fails during install:

```bash
cd /opt/stock-ticker-service
sudo ./venv/bin/pip install -r requirements.txt
sudo ./venv/bin/python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. proto/stock_ticker.proto
```