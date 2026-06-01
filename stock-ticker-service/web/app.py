import json
import os
import sys
import uuid
from pathlib import Path

import grpc
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
SERVICE_ROOT = PROJECT_DIR.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from proto import stock_ticker_pb2 as stock_ticker_pb2
from proto import stock_ticker_pb2_grpc as stock_ticker_pb2_grpc


app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path='')


def grpc_target() -> str:
    return os.getenv('STOCK_TICKER_GRPC_ADDR', '127.0.0.1:50053')


def get_stub() -> stock_ticker_pb2_grpc.StockTickerServiceStub:
    channel = grpc.insecure_channel(grpc_target())
    return stock_ticker_pb2_grpc.StockTickerServiceStub(channel)


def serialize_symbol(symbol: stock_ticker_pb2.StockSymbol) -> dict:
    return {
        'symbol': symbol.symbol,
        'company_name': symbol.company_name,
        'sector': symbol.sector,
        'base_price': symbol.base_price,
    }


def serialize_update(update: stock_ticker_pb2.StockUpdate) -> dict:
    return {
        'symbol': update.symbol,
        'price': update.price,
        'change': update.change,
        'change_percent': update.change_percent,
        'timestamp': update.timestamp,
        'volume': update.volume,
        'market_status': update.market_status,
    }


@app.get('/')
def index() -> Response:
    return send_from_directory(BASE_DIR, 'index.html')


@app.get('/healthz')
def healthz() -> Response:
    return jsonify({'ok': True, 'grpc_target': grpc_target()})


@app.get('/api/overview')
def overview() -> Response:
    return jsonify({
        'service': 'stockticker.StockTickerService',
        'grpc_target': grpc_target(),
        'rpc_methods': [
            'GetAvailableSymbols',
            'GetCurrentPrice',
            'SubscribeToTicker',
        ],
        'browser_endpoints': [
            'GET /api/symbols',
            'GET /api/price/<symbol>',
            'GET /api/stream?symbol=<symbol>&client_id=<id>',
        ],
    })


@app.get('/api/symbols')
def get_symbols() -> Response:
    stub = get_stub()
    response = stub.GetAvailableSymbols(stock_ticker_pb2.GetSymbolsRequest())
    return jsonify({'symbols': [serialize_symbol(symbol) for symbol in response.symbols]})


@app.get('/api/price/<symbol>')
def get_price(symbol: str) -> Response:
    stub = get_stub()
    response = stub.GetCurrentPrice(stock_ticker_pb2.GetPriceRequest(symbol=symbol))
    if not response.success:
        return jsonify({'success': False, 'error_message': response.error_message}), 404

    return jsonify({
        'success': True,
        'current_price': serialize_update(response.current_price),
    })


@app.get('/api/stream')
def stream_prices() -> Response:
    symbol = request.args.get('symbol', '').strip()
    client_id = request.args.get('client_id', '').strip() or f'web-{uuid.uuid4().hex[:12]}'

    if not symbol:
        return jsonify({'error': 'symbol is required'}), 400

    def generate():
        stub = get_stub()
        grpc_request = stock_ticker_pb2.SubscribeRequest(symbol=symbol, client_id=client_id)

        try:
            for update in stub.SubscribeToTicker(grpc_request):
                yield f"data: {json.dumps(serialize_update(update))}\n\n"
        except grpc.RpcError as exc:
            payload = {
                'code': exc.code().name if exc.code() else 'UNKNOWN',
                'details': exc.details() or 'stream failed',
            }
            yield f"event: error\ndata: {json.dumps(payload)}\n\n"

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)


if __name__ == '__main__':
    host = os.getenv('STOCK_TICKER_WEB_HOST', '127.0.0.1')
    port = int(os.getenv('STOCK_TICKER_WEB_PORT', '8080'))
    app.run(host=host, port=port, debug=False, threaded=True)