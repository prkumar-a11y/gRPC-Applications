# Stock Ticker Service - Web Examples

This document focuses on the stock ticker browser UI, the Python web bridge that serves it, and JavaScript usage patterns for `stock-ticker-service`.

## Current Transport Model

The service currently exposes native gRPC, and this folder now includes a lightweight Flask web bridge that serves a browser dashboard.

Current pieces:

- Native gRPC backend in `main.py`
- Browser UI at `web/index.html`
- Python web bridge at `web/app.py`

The bridge calls the gRPC service and exposes browser-friendly endpoints:

- `GET /` serves the dashboard
- `GET /api/symbols` returns available symbols
- `GET /api/price/<symbol>` returns a JSON snapshot
- `GET /api/stream?symbol=AAPL` streams updates over Server-Sent Events

When proxied through Apache on `/stock-ticker/`, the browser-facing URLs become:

- `GET /stock-ticker/`
- `GET /stock-ticker/api/symbols`
- `GET /stock-ticker/api/price/<symbol>`
- `GET /stock-ticker/api/stream?symbol=AAPL`

## Run The Web UI

Start the gRPC backend first:

```bash
cd stock-ticker-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash ./generate.sh
python3 main.py
```

Then start the web bridge in a second terminal:

```bash
cd stock-ticker-service
source .venv/bin/activate
python3 web/app.py
```

Open the dashboard at:

```text
http://127.0.0.1:8080
```

If Apache is proxying the UI under TLS, open:

```text
https://your-hostname/stock-ticker/
```

Optional environment variables:

```bash
STOCK_TICKER_GRPC_ADDR=127.0.0.1:50053 python3 web/app.py
STOCK_TICKER_WEB_HOST=0.0.0.0 STOCK_TICKER_WEB_PORT=8080 python3 web/app.py
```

## What The Web Page Does

- Loads the available stock symbols from the gRPC backend
- Fetches an initial snapshot for the selected symbol
- Opens a live SSE stream through the web bridge
- Renders current price, delta, volume, market state, and a sparkline
- Lets you switch symbols or supply a custom symbol such as `AAPL:5`

- Local backend: `127.0.0.1:50053`
- Optional Apache TLS proxy: `https://<host>:443`
- Service name: `stockticker.StockTickerService`

That means:

- `grpcurl` works directly
- Node.js gRPC clients work directly
- Browsers do **not** speak native gRPC directly with `fetch`
- Browser apps need either a backend-for-frontend layer or a dedicated gRPC-Web proxy

This repository now includes the backend-for-frontend style bridge in `web/app.py`.

For the core service overview, see [stock-ticker-service/README.md](stock-ticker-service/README.md).

## Available RPCs

- `GetAvailableSymbols`
- `GetCurrentPrice`
- `SubscribeToTicker`

## Example 1: Test With grpcurl

List services:

```bash
grpcurl -plaintext localhost:50053 list
```

Get the current price:

```bash
grpcurl -plaintext \
  -d '{"symbol":"AAPL"}' \
  localhost:50053 \
  stockticker.StockTickerService/GetCurrentPrice
```

Stream updates:

```bash
grpcurl -plaintext \
  -d '{"symbol":"AAPL","client_id":"web-demo"}' \
  localhost:50053 \
  stockticker.StockTickerService/SubscribeToTicker
```

If Apache is proxying the service on `443`:

```bash
grpcurl -insecure \
  -d '{"symbol":"AAPL"}' \
  your-hostname:443 \
  stockticker.StockTickerService/GetCurrentPrice
```

## Example 2: Node.js Client

This example uses native gRPC from Node.js, which works with the current service as-is.

### Install Packages

```bash
npm install @grpc/grpc-js @grpc/proto-loader
```

### Example Script

```js
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

const protoPath = path.resolve(__dirname, '../proto/stock_ticker.proto');
const packageDefinition = protoLoader.loadSync(protoPath, {
  keepCase: false,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const proto = grpc.loadPackageDefinition(packageDefinition).stockticker;

const client = new proto.StockTickerService(
  'localhost:50053',
  grpc.credentials.createInsecure()
);

client.GetCurrentPrice({ symbol: 'AAPL' }, (error, response) => {
  if (error) {
    console.error('GetCurrentPrice failed:', error);
    return;
  }

  console.log('Current price response:', response);
});
```

### Streaming Example

```js
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

const protoPath = path.resolve(__dirname, '../proto/stock_ticker.proto');
const packageDefinition = protoLoader.loadSync(protoPath, {
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const proto = grpc.loadPackageDefinition(packageDefinition).stockticker;
const client = new proto.StockTickerService(
  'localhost:50053',
  grpc.credentials.createInsecure()
);

const stream = client.SubscribeToTicker({
  symbol: 'AAPL:5',
  client_id: 'node-example',
});

stream.on('data', (update) => {
  console.log('Price update:', update);
});

stream.on('end', () => {
  console.log('Stream ended');
});

stream.on('error', (error) => {
  console.error('Stream failed:', error);
});
```

## Example 3: Node.js Client Through 443

If Apache is proxying native gRPC on `443`, switch the target to your TLS endpoint.

For publicly trusted certificates:

```js
const client = new proto.StockTickerService(
  'your-hostname:443',
  grpc.credentials.createSsl()
);
```

For self-signed certificates, provide the CA bundle explicitly:

```js
const fs = require('fs');

const rootCert = fs.readFileSync('/path/to/ca.pem');
const client = new proto.StockTickerService(
  'your-hostname:443',
  grpc.credentials.createSsl(rootCert)
);
```

## Browser Usage

### Important Limitation

The current service and Apache setup support **native gRPC**, not browser-native `fetch` calls to gRPC methods.

If you need a web frontend in the browser, use one of these patterns:

1. A backend-for-frontend service in Node/Go/Python that calls the gRPC service.
2. A gRPC-Web proxy such as Envoy.
3. A REST bridge layer for browser clients.

## Example 4: Browser Architecture With a BFF

Recommended production-friendly flow:

```text
Browser UI -> BFF API -> stock-ticker-service gRPC backend
```

That keeps the browser on simple HTTP/JSON while the BFF talks native gRPC.

### Minimal Express Example

```js
const express = require('express');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

const app = express();
const protoPath = path.resolve(__dirname, '../proto/stock_ticker.proto');
const packageDefinition = protoLoader.loadSync(protoPath, {
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const proto = grpc.loadPackageDefinition(packageDefinition).stockticker;
const client = new proto.StockTickerService(
  'localhost:50053',
  grpc.credentials.createInsecure()
);

app.get('/api/price/:symbol', (req, res) => {
  client.GetCurrentPrice({ symbol: req.params.symbol }, (error, response) => {
    if (error) {
      res.status(500).json({ error: error.message });
      return;
    }
    res.json(response);
  });
});

app.listen(8080, () => {
  console.log('Web API listening on :8080');
});
```

The browser can then call:

```js
const response = await fetch('/api/price/AAPL');
const data = await response.json();
console.log(data);
```

## Example 5: Browser Usage With gRPC-Web

If you add a gRPC-Web compatible proxy later, you can generate web stubs and call the service from the browser.

Example generation command:

```bash
protoc -I=. proto/stock_ticker.proto \
  --js_out=import_style=commonjs:web/generated \
  --grpc-web_out=import_style=typescript,mode=grpcwebtext:web/generated
```

Example client shape:

```ts
import { StockTickerServiceClient } from './generated/Stock_tickerServiceClientPb';
import { GetPriceRequest } from './generated/stock_ticker_pb';

const client = new StockTickerServiceClient('https://your-hostname');
const request = new GetPriceRequest();
request.setSymbol('AAPL');

client.getCurrentPrice(request, {}, (error, response) => {
  if (error) {
    console.error(error.message);
    return;
  }

  console.log(response.toObject());
});
```

This example requires infrastructure that is **not** currently included in this repository.

## Recommended Approach

For the current repo state:

- Use `grpcurl` for quick validation
- Use Node.js with `@grpc/grpc-js` for service-to-service integration
- Use a BFF if you need browser-based UI quickly
- Add gRPC-Web only if you specifically need direct browser-to-gRPC calls