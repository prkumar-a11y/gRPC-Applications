import grpc
from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from concurrent import futures
import time
import threading
import random
import logging
import os
import signal
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Import generated protobuf classes
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from proto import stock_ticker_pb2 as stock_ticker_pb2
from proto import stock_ticker_pb2_grpc as stock_ticker_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(threadName)s %(thread)d] - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockTickerService(stock_ticker_pb2_grpc.StockTickerServiceServicer):
    def __init__(self):
        # Sample stock data with starting prices
        self.stock_data = {
            'AKAM': {'company': 'Akamai Technologies Inc.', 'sector': 'Technology', 'price': 75.30, 'volume': 300000},
            'AAPL': {'company': 'Apple Inc.', 'sector': 'Technology', 'price': 230.50, 'volume': 1000000},
            'GOOGL': {'company': 'Alphabet Inc.', 'sector': 'Technology', 'price': 250.75, 'volume': 500000},
            'TSLA': {'company': 'Tesla Inc.', 'sector': 'Automotive', 'price': 250.30, 'volume': 2000000},
            'MSFT': {'company': 'Microsoft Corporation', 'sector': 'Technology', 'price': 420.90, 'volume': 800000},
            'AMZN': {'company': 'Amazon.com Inc.', 'sector': 'E-commerce', 'price': 3400.25, 'volume': 600000},
            'NVDA': {'company': 'NVIDIA Corporation', 'sector': 'Technology', 'price': 480.60, 'volume': 1500000},
            'META': {'company': 'Meta Platforms Inc.', 'sector': 'Technology', 'price': 350.75, 'volume': 900000},
            'NFLX': {'company': 'Netflix Inc.', 'sector': 'Entertainment', 'price': 450.20, 'volume': 700000},
        }
        
        logger.info("Initializing stock data:")
        for symbol, data in self.stock_data.items():
            logger.info(f"  {symbol}: {data['company']} @ ${data['price']:.2f}, volume: {data['volume']:,}")
        
        # Validate initial data
        for symbol, data in self.stock_data.items():
            if data['volume'] <= 0 or data['volume'] > 10000000:
                logger.warning(f"Invalid initial volume for {symbol}: {data['volume']}")
                data['volume'] = 1000000  # Reset to safe value
        
        # Track active subscriptions
        self.active_subscriptions = defaultdict(list)
        self.subscription_lock = threading.Lock()
        
        # Start the price update thread
        self.price_update_thread = threading.Thread(target=self._update_prices_continuously, daemon=True)
        self.price_update_thread.start()
        
        logger.info("Stock Ticker Service initialized with %d symbols", len(self.stock_data))

    def _get_market_status(self):
        """Simple market status simulation based on time"""
        hour = datetime.now().hour
        if 9 <= hour < 16:
            return "OPEN"
        elif 4 <= hour < 9:
            return "PRE_MARKET"
        elif 16 <= hour < 20:
            return "AFTER_HOURS"
        else:
            return "CLOSED"

    def _generate_price_update(self, symbol):
        """Generate a random price update for a given symbol"""
        if symbol not in self.stock_data:
            logger.warning(f"Attempted to generate update for unknown symbol: {symbol}")
            return None
            
        stock_info = self.stock_data[symbol]
        current_price = stock_info['price']
        
        logger.debug(f"Generating price update for {symbol}: current_price={current_price}")
        
        # Generate random price change between -5% and +5%
        change_percent = random.uniform(-0.05, 0.05)
        price_change = current_price * change_percent
        new_price = max(current_price + price_change, 0.01)  # Ensure price doesn't go negative
        
        logger.debug(f"Price calculation for {symbol}: change_percent={change_percent:.4f}, price_change={price_change:.4f}, new_price={new_price:.4f}")
        
        # Update the stored price
        stock_info['price'] = new_price
        
        # Simulate volume changes - use base volume, not current volume to prevent exponential growth
        base_volume = self.stock_data[symbol]['volume']  # Get original base volume
        volume_change = random.uniform(-0.3, 0.7)  # Volume can vary more dramatically
        new_volume = int(base_volume * (1 + volume_change))
        
        logger.debug(f"Volume calculation for {symbol}: base_volume={base_volume}, volume_change={volume_change:.4f}, raw_new_volume={base_volume * (1 + volume_change):.0f}")
        
        # Keep volume within reasonable bounds
        new_volume = max(1000, min(new_volume, 10000000))  # Between 1K and 10M shares
        
        logger.debug(f"Volume bounded for {symbol}: final_volume={new_volume}")
        
        # Get current timestamp
        current_time = int(time.time())
        
        logger.debug(f"Timestamp for {symbol}: {current_time}")
        
        try:
            update = stock_ticker_pb2.StockUpdate(
                symbol=symbol,
                price=round(new_price, 2),
                change=round(price_change, 2),
                change_percent=round(change_percent * 100, 2),
                timestamp=current_time,
                volume=new_volume,
                market_status=self._get_market_status()
            )
            
            logger.debug(f"Successfully created StockUpdate protobuf for {symbol}: price={update.price}, change={update.change}, change_percent={update.change_percent}, volume={update.volume}, timestamp={update.timestamp}, market_status={update.market_status}")
            return update
            
        except Exception as e:
            logger.error(f"Error creating StockUpdate protobuf for {symbol}: {e}")
            logger.error(f"Values that caused error: symbol={symbol}, price={round(new_price, 2)}, change={round(price_change, 2)}, change_percent={round(change_percent * 100, 2)}, timestamp={current_time}, volume={new_volume}, market_status={self._get_market_status()}")
            return None

    def _update_prices_continuously(self):
        """Background thread that updates prices every 5 seconds"""
        logger.info("Price update thread started")
        update_count = 0
        
        while True:
            try:
                time.sleep(5)  # Update every 5 seconds
                update_count += 1
                
                logger.debug(f"Starting price update cycle #{update_count}")
                
                with self.subscription_lock:
                    # Get all symbols that have active subscriptions
                    symbols_to_update = list(self.active_subscriptions.keys())
                
                logger.debug(f"Symbols with active subscriptions: {symbols_to_update}")
                
                for symbol in symbols_to_update:
                    logger.debug(f"Generating price update for {symbol}")
                    price_update = self._generate_price_update(symbol)
                    
                    if price_update:
                        # Validate the update before sending
                        logger.debug(f"Validating update for {symbol}: volume={price_update.volume}, timestamp={price_update.timestamp}")
                        
                        if price_update.volume < 0 or price_update.volume > 100000000:
                            logger.error(f"Invalid volume for {symbol}: {price_update.volume} (must be between 0 and 100,000,000)")
                            continue
                        if price_update.timestamp < 1000000000 or price_update.timestamp > 2000000000:
                            logger.error(f"Invalid timestamp for {symbol}: {price_update.timestamp} (must be reasonable Unix timestamp)")
                            continue
                            
                        logger.info(f"Generated valid update for {symbol}: price=${price_update.price:.2f}, change={price_update.change:+.2f}, volume={price_update.volume:,}, market_status={price_update.market_status}")
                        
                        with self.subscription_lock:
                            # Send update to all subscribers of this symbol
                            subscribers = self.active_subscriptions[symbol][:]
                            logger.debug(f"Sending update to {len(subscribers)} subscribers for {symbol}")
                            
                        for i, subscriber_queue in enumerate(subscribers):
                            try:
                                logger.debug(f"Sending update to subscriber {i+1} for {symbol}")
                                subscriber_queue.put(price_update)
                                logger.debug(f"Successfully sent update to subscriber {i+1} for {symbol}")
                            except Exception as e:
                                logger.error(f"Error sending update to subscriber {i+1} for {symbol}: {e}")
                                # Remove failed subscriber
                                with self.subscription_lock:
                                    if subscriber_queue in self.active_subscriptions[symbol]:
                                        self.active_subscriptions[symbol].remove(subscriber_queue)
                                        logger.info(f"Removed failed subscriber for {symbol}")
                                        
            except Exception as e:
                logger.error(f"Error in price update thread (cycle #{update_count}): {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue the loop despite errors

    def SubscribeToTicker(self, request, context):
        """Subscribe to stock price updates for a given symbol"""
        # Validate input data
        if not request.symbol or request.symbol.strip() == "":
            logger.warning(f"Client sent empty symbol")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Payload not as expected: symbol cannot be empty')
            return
        
        if not request.client_id or request.client_id.strip() == "":
            logger.warning(f"Client sent empty client_id")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Payload not as expected: client_id cannot be empty')
            return
        
        if len(request.symbol) > 10:
            logger.warning(f"Client sent symbol exceeding max length: {request.symbol}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Payload not as expected: symbol exceeds maximum length of 10 characters')
            return
        
        if len(request.client_id) > 100:
            logger.warning(f"Client sent client_id exceeding max length")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Payload not as expected: client_id exceeds maximum length of 100 characters')
            return
        
        raw_symbol = request.symbol.strip()
        symbol = raw_symbol.upper()
        max_updates = None
        # Allow ad-hoc limiting syntax: SYMBOL:COUNT (e.g. AAPL:5) without proto change
        if ':' in raw_symbol:
            parts = raw_symbol.split(':', 1)
            if parts[0]:
                symbol = parts[0].upper()
            try:
                candidate = parts[1].strip()
                if candidate:
                    max_updates = int(candidate)
                    if max_updates <= 0:
                        max_updates = None
            except ValueError:
                max_updates = None  # Ignore malformed suffix
        if max_updates:
            logger.info(f"Subscription will terminate after {max_updates} updates for symbol {symbol}")
        client_id = request.client_id
        
        logger.info(f"New subscription request: client={client_id}, symbol={symbol}")
        
        if symbol not in self.stock_data:
            logger.warning(f"Client {client_id} requested unknown symbol: {symbol}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'Stock symbol {symbol} not found')
            return
            
        logger.info(f"Client {client_id} subscribing to {symbol}")
        
        # Create a queue for this subscriber
        import queue
        subscriber_queue = queue.Queue()
        
        # Add subscriber to the list
        with self.subscription_lock:
            self.active_subscriptions[symbol].append(subscriber_queue)
            logger.info(f"Added subscriber {client_id} to {symbol}. Total subscribers for {symbol}: {len(self.active_subscriptions[symbol])}")
            
        # Send initial price update
        logger.debug(f"Sending initial price update to {client_id} for {symbol}")
        initial_update = self._generate_price_update(symbol)
        if initial_update:
            logger.info(f"Sending initial update to {client_id}: {symbol} @ ${initial_update.price:.2f}")
            yield initial_update
        else:
            logger.error(f"Failed to generate initial update for {client_id}, symbol {symbol}")
        
        # Count initial update towards max_updates
        update_count = 1 if initial_update else 0
        if max_updates and update_count >= max_updates:
            logger.info(f"Reached max_updates={max_updates} after initial update for {client_id} symbol {symbol}; closing stream")
            return
        try:
            # Stream updates to the client
            while True:
                try:
                    # Wait for new price update
                    logger.debug(f"Client {client_id} waiting for update on {symbol}")
                    update = subscriber_queue.get(timeout=30)  # 30 second timeout
                    update_count += 1
                    
                    logger.info(f"Sending update #{update_count} to {client_id}: {symbol} @ ${update.price:.2f} (change: {update.change:+.2f}, volume: {update.volume:,})")
                    yield update
                    if max_updates and update_count >= max_updates:
                        logger.info(f"Reached max_updates={max_updates} for client {client_id} symbol {symbol}; closing stream")
                        break
                    
                except queue.Empty:
                    # Send a heartbeat/current price if no updates
                    logger.debug(f"No updates received for {client_id} on {symbol}, sending heartbeat")
                    heartbeat = self._generate_price_update(symbol)
                    if heartbeat:
                        logger.debug(f"Sending heartbeat to {client_id}: {symbol} @ ${heartbeat.price:.2f}")
                        yield heartbeat
                    else:
                        logger.warning(f"Failed to generate heartbeat for {client_id}, symbol {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error in subscription loop for {client_id}, symbol {symbol}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Subscription error for client {client_id}, symbol {symbol}: {e}")
            import traceback
            logger.error(f"Subscription traceback: {traceback.format_exc()}")
            
        finally:
            # Clean up subscription
            with self.subscription_lock:
                if subscriber_queue in self.active_subscriptions[symbol]:
                    self.active_subscriptions[symbol].remove(subscriber_queue)
                    logger.info(f"Client {client_id} unsubscribed from {symbol}. Remaining subscribers: {len(self.active_subscriptions[symbol])}")

    def GetAvailableSymbols(self, request, context):
        """Get list of available stock symbols"""
        logger.info("GetAvailableSymbols request received")
        
        symbols = []
        for symbol, info in self.stock_data.items():
            symbol_info = stock_ticker_pb2.StockSymbol(
                symbol=symbol,
                company_name=info['company'],
                sector=info['sector'],
                base_price=info['price']
            )
            symbols.append(symbol_info)
            logger.debug(f"Added symbol: {symbol} - {info['company']} @ ${info['price']:.2f}")
            
        response = stock_ticker_pb2.GetSymbolsResponse(symbols=symbols)
        logger.info(f"Returning {len(symbols)} available symbols")
        return response

    def GetCurrentPrice(self, request, context):
        """Get current price for a specific symbol"""
        # Validate input data
        if not request.symbol or request.symbol.strip() == "":
            logger.warning(f"GetCurrentPrice called with empty symbol")
            return stock_ticker_pb2.GetPriceResponse(
                success=False,
                error_message="Payload not as expected: symbol cannot be empty"
            )
        
        if len(request.symbol) > 10:
            logger.warning(f"GetCurrentPrice called with symbol exceeding max length: {request.symbol}")
            return stock_ticker_pb2.GetPriceResponse(
                success=False,
                error_message="Payload not as expected: symbol exceeds maximum length of 10 characters"
            )
        
        symbol = request.symbol.upper()
        
        logger.info(f"GetCurrentPrice request for symbol: {symbol}")
        
        if symbol not in self.stock_data:
            logger.warning(f"GetCurrentPrice requested unknown symbol: {symbol}")
            return stock_ticker_pb2.GetPriceResponse(
                success=False,
                error_message=f"Symbol {symbol} not found"
            )
            
        current_update = self._generate_price_update(symbol)
        if current_update:
            logger.info(f"Returning current price for {symbol}: ${current_update.price:.2f}")
            return stock_ticker_pb2.GetPriceResponse(
                current_price=current_update,
                success=True
            )
        else:
            logger.error(f"Failed to generate current price for {symbol}")
            return stock_ticker_pb2.GetPriceResponse(
                success=False,
                error_message=f"Failed to generate price for {symbol}"
            )

def serve():
    """Start the gRPC server"""
    logger.info("Starting Stock Ticker Service...")
    
    # Configure server with proper keepalive settings and larger thread pool
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=50),
        options=[
            # Keepalive settings to prevent connection drops
            ('grpc.keepalive_time_ms', 10000),  # Send keepalive ping every 10 seconds
            ('grpc.keepalive_timeout_ms', 5000),  # Wait 5 seconds for ping ack
            ('grpc.keepalive_permit_without_calls', True),  # Allow keepalive pings without active calls
            ('grpc.http2.max_pings_without_data', 0),  # No limit on pings without data
            ('grpc.http2.min_time_between_pings_ms', 10000),  # Min 10 seconds between pings
            ('grpc.http2.min_ping_interval_without_data_ms', 5000),  # Min 5 seconds between pings without data
            # Connection settings
            ('grpc.max_connection_idle_ms', 300000),  # Max 5 minutes idle
            ('grpc.max_connection_age_ms', 600000),  # Max 10 minutes connection age
            ('grpc.max_connection_age_grace_ms', 30000),  # 30 seconds grace period
            # Buffer sizes
            ('grpc.max_send_message_length', 10 * 1024 * 1024),  # 10 MB
            ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # 10 MB
        ]
    )
    
    stock_ticker_pb2_grpc.add_StockTickerServiceServicer_to_server(
        StockTickerService(), server
    )
    
    # Add health check service
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=futures.ThreadPoolExecutor(max_workers=5)
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set('stockticker.StockTickerService', health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set('', health_pb2.HealthCheckResponse.SERVING)  # Overall server health
    
    # Enable reflection for grpcurl and other tools
    SERVICE_NAMES = (
        'stockticker.StockTickerService',
        health_pb2.DESCRIPTOR.services_by_name['Health'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    
    listen_host = os.getenv('STOCK_TICKER_HOST', '0.0.0.0')
    listen_port = os.getenv('STOCK_TICKER_PORT', '50053')
    listen_addr = f'{listen_host}:{listen_port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting Stock Ticker Service on {listen_addr}")
    logger.info("gRPC reflection and health checks enabled")
    server.start()
    
    # Graceful shutdown handler
    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        health_servicer.enter_graceful_shutdown()
        server.stop(30)  # 30 seconds grace period
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    try:
        logger.info("Stock Ticker Service is now running and accepting connections")
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping Stock Ticker Service")
        health_servicer.enter_graceful_shutdown()
        server.stop(30)
    except Exception as e:
        logger.error(f"Unexpected error in server: {e}")
        health_servicer.enter_graceful_shutdown()
        server.stop(0)

if __name__ == '__main__':
    serve()