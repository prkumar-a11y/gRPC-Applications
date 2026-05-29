# Stock Ticker gRPC - Linux Deployment Guide

This guide installs the Python stock ticker gRPC server on Ubuntu-style Linux hosts such as `Linux a198-18-76-38 5.15.0-134-generic`.

## Prerequisites

- Ubuntu or another `apt`-based Linux distribution
- `sudo` access
- Port `50053/tcp` reachable locally on the host
- If serving gRPC on `443`, Apache with `mod_ssl`, `mod_proxy`, and `mod_http2`

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
- Installs `systemd` units named `stock-ticker` and `stock-ticker-web`

## Service Commands

```bash
sudo systemctl start stock-ticker
sudo systemctl enable stock-ticker
sudo systemctl start stock-ticker-web
sudo systemctl enable stock-ticker-web
sudo systemctl status stock-ticker
sudo systemctl status stock-ticker-web
sudo journalctl -u stock-ticker -f
```

By default, the installed `systemd` service binds the gRPC backend to `127.0.0.1:50053` so it can sit behind a reverse proxy on `443`.
The installed web bridge binds to `127.0.0.1:8080` by default, or whatever value you set in `STOCK_TICKER_WEB_PORT`, and serves the dashboard plus browser-friendly `/api/*` endpoints.

## Verify The Port

```bash
sudo ss -ltnp | grep 50053
```

## Verify Health With grpcurl

Install `grpcurl` if needed, then run against the backend directly:

```bash
grpcurl -plaintext localhost:50053 list
grpcurl -plaintext localhost:50053 stockticker.StockTickerService/GetAvailableSymbols
grpcurl -plaintext -d '{"symbol":"AAPL"}' localhost:50053 stockticker.StockTickerService/GetCurrentPrice
```

## Apache On 443

Enable the required modules:

```bash
sudo a2enmod ssl proxy proxy_http proxy_http2 headers
sudo systemctl restart apache2
```

Install the sample vhost from [stock-ticker-service/deploy/apache-stock-ticker-443.conf](stock-ticker-service/deploy/apache-stock-ticker-443.conf) into your Apache site configuration, then update `ServerName` and certificate paths.

Example install steps on Ubuntu:

```bash
sudo cp deploy/apache-stock-ticker-443.conf /etc/apache2/sites-available/stock-ticker.conf
sudoedit /etc/apache2/sites-available/stock-ticker.conf
sudo a2ensite stock-ticker.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

After the two systemd services are running and Apache is reloaded, the stock ticker browser page is available at:

```text
https://your-hostname/stock-ticker/
```

With Apache proxying TLS on `443`, test externally with:

```bash
curl -k https://your-hostname/stock-ticker/healthz
grpcurl your-hostname:443 list
grpcurl -d '{"symbol":"AAPL"}' your-hostname:443 stockticker.StockTickerService/GetCurrentPrice
grpcurl -d '{"symbol":"AAPL:5","client_id":"grpcurl-test"}' your-hostname:443 stockticker.StockTickerService/SubscribeToTicker
```

If you use a self-signed certificate, add `-insecure` to `grpcurl`.

## Remote Access

If you are not using Apache on `443`, open `50053/tcp` on the host firewall and connect from your client machine using the server's IP address:

```bash
grpcurl -plaintext 198.18.76.38:50053 list
```

## Troubleshooting

If the service does not start:

```bash
sudo systemctl status stock-ticker
sudo systemctl status stock-ticker-web
sudo journalctl -u stock-ticker -n 100 --no-pager
sudo journalctl -u stock-ticker-web -n 100 --no-pager
```

If protobuf generation fails during install:

```bash
cd /opt/stock-ticker-service
sudo ./venv/bin/pip install -r requirements.txt
sudo ./venv/bin/python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. proto/stock_ticker.proto
```