# Stock Ticker Service - Streaming gRPC Application

A Python gRPC stock ticker service that supports unary and server-streaming RPCs for simulated stock prices.

## Features

- **SubscribeToTicker**: Stream stock price updates for a symbol
- **GetAvailableSymbols**: List the supported stock symbols
- **GetCurrentPrice**: Fetch the current simulated price for one symbol
- **Health Checks**: gRPC health service enabled
- **Reflection**: gRPC reflection enabled for `grpcurl`

## Project Structure

```text
stock-ticker-service/
├── proto/
│   ├── __init__.py                 # Python package marker for generated stubs
│   └── stock_ticker.proto          # Protocol Buffer definitions
├── deploy/
│   ├── DEPLOYMENT.md               # Linux deployment guide
│   ├── apache-stock-ticker-443.conf# Apache TLS proxy example for port 443
│   ├── install-from-git.sh         # Install directly from Git
│   ├── install.sh                  # Linux installer
│   └── stock-ticker.service        # systemd unit file
├── Dockerfile                      # Container build
├── generate.sh                     # Generate Python gRPC stubs
├── main.py                         # Service implementation
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Prerequisites

- Python 3.10 or higher
- `pip`
- gRPC Python dependencies from `requirements.txt`

## Installation

```bash
cd stock-ticker-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Protocol Buffers

Generate the Python protobuf and gRPC files from `proto/stock_ticker.proto`:

```bash
bash ./generate.sh
```

This generates:

- `proto/stock_ticker_pb2.py`
- `proto/stock_ticker_pb2_grpc.py`

## Running

### Start Server

```bash
cd stock-ticker-service
source .venv/bin/activate
bash ./generate.sh
python3 main.py
```

The server listens on `0.0.0.0:50053` by default.

You can override the bind address with environment variables:

```bash
STOCK_TICKER_HOST=127.0.0.1 STOCK_TICKER_PORT=50053 python3 main.py
```

### Start Web UI

In another terminal, run the web bridge:

```bash
cd stock-ticker-service
source .venv/bin/activate
python3 web/app.py
```

Then open `http://127.0.0.1:8080` in your browser.

## API Overview

### Messages

- `SubscribeRequest`: Symbol and client identifier for a streaming subscription
- `StockUpdate`: Current price, price delta, percentage change, timestamp, volume, and market status
- `GetSymbolsRequest`: Empty request for symbol listing
- `StockSymbol`: Symbol metadata including company name and sector
- `GetSymbolsResponse`: Repeated list of available symbols
- `GetPriceRequest`: Request for one symbol
- `GetPriceResponse`: Current price plus success/error state

### Service Methods

1. **SubscribeToTicker(SubscribeRequest) -> stream StockUpdate**
   - Streams an initial update immediately and then periodic updates for the requested symbol

2. **GetAvailableSymbols(GetSymbolsRequest) -> GetSymbolsResponse**
   - Returns all supported symbols and company metadata

3. **GetCurrentPrice(GetPriceRequest) -> GetPriceResponse**
   - Returns one current simulated price for the requested symbol

## Example Usage With grpcurl

Start the server first, then test from another terminal.

List services:

```bash
grpcurl -plaintext localhost:50053 list
```

Get available symbols:

```bash
grpcurl -plaintext \
  localhost:50053 \
  stockticker.StockTickerService/GetAvailableSymbols
```

Get one symbol price:

```bash
grpcurl -plaintext \
  -d '{"symbol":"AAPL"}' \
  localhost:50053 \
  stockticker.StockTickerService/GetCurrentPrice
```

Subscribe to streaming updates:

```bash
grpcurl -plaintext \
  -d '{"symbol":"AAPL","client_id":"test-client-1"}' \
  localhost:50053 \
  stockticker.StockTickerService/SubscribeToTicker
```

Limit a stream to a fixed number of updates using the `SYMBOL:COUNT` shorthand:

```bash
grpcurl -plaintext \
  -d '{"symbol":"AAPL:5","client_id":"test-client-1"}' \
  localhost:50053 \
  stockticker.StockTickerService/SubscribeToTicker
```

## Testing

```bash
# Terminal 1
cd stock-ticker-service
source .venv/bin/activate
bash ./generate.sh
python3 main.py

# Terminal 2
grpcurl -plaintext localhost:50053 list
grpcurl -plaintext -d '{"symbol":"AAPL"}' localhost:50053 stockticker.StockTickerService/GetCurrentPrice
grpcurl -plaintext -d '{"symbol":"AAPL","client_id":"demo-client"}' localhost:50053 stockticker.StockTickerService/SubscribeToTicker

# Terminal 3
python3 web/app.py
# open http://127.0.0.1:8080
```

## Linux Deployment

For Ubuntu and `systemd` deployment, see [stock-ticker-service/deploy/DEPLOYMENT.md](stock-ticker-service/deploy/DEPLOYMENT.md).

For the runnable browser UI, Node.js examples, and web-focused integration notes, see [stock-ticker-service/web/README.md](stock-ticker-service/web/README.md).

That guide also covers:

- Installing the service under `/opt/stock-ticker-service`
- Running the backend on `127.0.0.1:50053`
- Exposing the service through Apache on `443`

## Docker

Build and run locally:

```bash
docker build -t stock-ticker-service .
docker run --rm -p 50053:50053 stock-ticker-service
```

## Notes

- Stock data is simulated in memory and resets on restart
- The backend gRPC server is insecure by default; TLS can be terminated by Apache on `443`
- Reflection and health services are enabled to simplify `grpcurl` testing