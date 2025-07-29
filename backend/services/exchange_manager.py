import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from exchanges.bitunix import BitUnixExchange
    from exchanges.lmex import LMEXExchange
    from exchanges.base import ExchangeInterface, ExchangeOrderRequest
except ImportError:
    # Fallback imports for development
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, parent_dir)
    from exchanges.bitunix import BitUnixExchange
    from exchanges.lmex import LMEXExchange
    from exchanges.base import ExchangeInterface, ExchangeOrderRequest
from backend.core.config import settings
from backend.models.market import Ticker, OrderBook, SymbolInfo, Candle
from backend.models.trading import OrderResponse, Position
from backend.models.account import Balance, AccountInfo
from backend.services.exchange_wrapper import ExchangeAsyncWrapper
from datetime import datetime

logger = logging.getLogger(__name__)


class ExchangeManager:
    def __init__(self):
        self._exchanges: Dict[str, ExchangeAsyncWrapper] = {}
        self._websocket_managers = {}
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize exchange connections"""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing exchange manager...")
            
            for exchange_name in settings.SUPPORTED_EXCHANGES:
                try:
                    await self._init_exchange(exchange_name)
                except Exception as e:
                    logger.error(f"Failed to initialize {exchange_name}: {e}")
            
            self._initialized = True
    
    async def _init_exchange(self, exchange_name: str):
        """Initialize a specific exchange"""
        from backend.services.api_key_service import api_key_service
        
        # Get API keys for the exchange
        keys = api_key_service.get_keys(exchange_name)
        
        if exchange_name == "bitunix":
            exchange = BitUnixExchange()
            if keys:
                api_key, api_secret = keys
                # Set credentials on the exchange
                if hasattr(exchange, 'set_credentials'):
                    exchange.set_credentials(api_key, api_secret)
                    logger.info(f"Set API credentials for {exchange_name}")
                else:
                    # For ccxt-based exchanges
                    exchange.apiKey = api_key
                    exchange.secret = api_secret
                    logger.info(f"Set API credentials for {exchange_name} (ccxt)")
            else:
                logger.warning(f"No API keys found for {exchange_name}, using public endpoints only")
                
        elif exchange_name == "lmex":
            exchange = LMEXExchange()
            if keys:
                api_key, api_secret = keys
                if hasattr(exchange, 'set_credentials'):
                    exchange.set_credentials(api_key, api_secret)
                else:
                    exchange.apiKey = api_key
                    exchange.secret = api_secret
                logger.info(f"Set API credentials for {exchange_name}")
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        # Wrap the exchange with async wrapper
        wrapped_exchange = ExchangeAsyncWrapper(exchange)
        self._exchanges[exchange_name] = wrapped_exchange
        
        # Test connectivity if we have API keys
        if keys:
            try:
                # Try to fetch balance as a connectivity test
                await wrapped_exchange.fetchBalance()
                logger.info(f"Successfully authenticated with {exchange_name}")
            except Exception as e:
                logger.error(f"Failed to authenticate with {exchange_name}: {e}")
        
        logger.info(f"Initialized {exchange_name} exchange")
    
    async def cleanup(self):
        """Cleanup all exchange connections"""
        async with self._lock:
            for ws_manager in self._websocket_managers.values():
                if hasattr(ws_manager, 'disconnect'):
                    await ws_manager.disconnect()
            
            self._exchanges.clear()
            self._websocket_managers.clear()
            self._initialized = False
    
    def get_exchange(self, exchange_name: str) -> ExchangeAsyncWrapper:
        """Get exchange instance by name"""
        if exchange_name not in self._exchanges:
            raise ValueError(f"Exchange {exchange_name} not initialized")
        return self._exchanges[exchange_name]
    
    async def get_connected_exchanges(self) -> List[str]:
        """Get list of connected exchanges"""
        return list(self._exchanges.keys())
    
    async def fetch_ticker(self, exchange: str, symbol: str) -> Ticker:
        """Fetch ticker for a symbol"""
        try:
            ex = self.get_exchange(exchange)
            
            # Fetch all tickers (BitUnix doesn't support single ticker fetch)
            tickers_list = await ex.fetchTickers()
            
            # Convert list to dict by symbol
            tickers = {}
            for ticker in tickers_list:
                if hasattr(ticker, 'symbol'):
                    tickers[ticker.symbol] = ticker
            
            if symbol not in tickers:
                raise ValueError(f"Symbol {symbol} not found on {exchange}")
            
            ticker = tickers[symbol]
            # ExchangeTicker is an object, not a dict
            from datetime import datetime
            return Ticker(
                symbol=symbol,
                base='',  # Not available in ExchangeTicker
                quote='',  # Not available in ExchangeTicker
                bid=Decimal(str(ticker.bidPrice)),
                ask=Decimal(str(ticker.askPrice)),
                last=Decimal(str(ticker.lastPrice)),
                high=Decimal('0'),  # Not available in ExchangeTicker
                low=Decimal('0'),  # Not available in ExchangeTicker
                volume=Decimal(str(ticker.volume)),
                quote_volume=Decimal('0'),  # Not available in ExchangeTicker
                change=Decimal('0'),  # Not available in ExchangeTicker
                change_percent=Decimal('0'),  # Not available in ExchangeTicker
                timestamp=datetime.now()  # Use current time since ExchangeTicker doesn't provide it
            )
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol} on {exchange}: {e}")
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed for {exchange}. Please check your API keys.")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise Exception(f"Rate limit exceeded on {exchange}. Please try again later.")
            else:
                raise Exception(f"Failed to fetch ticker for {symbol}: {str(e)}")
    
    async def fetch_all_tickers(self, exchange: str) -> List[Ticker]:
        """Fetch all tickers"""
        try:
            ex = self.get_exchange(exchange)
            tickers_list = await ex.fetchTickers()
        except Exception as e:
            logger.error(f"Error fetching tickers from {exchange}: {e}")
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed for {exchange}. Please check your API keys.")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise Exception(f"Rate limit exceeded on {exchange}. Please try again later.")
            else:
                raise Exception(f"Failed to fetch tickers: {str(e)}")
        
        result = []
        for ticker in tickers_list:
            try:
                # Handle ExchangeTicker objects
                symbol = ticker.symbol if hasattr(ticker, 'symbol') else str(ticker)
                result.append(Ticker(
                    symbol=symbol,
                    base='',  # BitUnix doesn't provide base/quote in ticker
                    quote='USDT',  # Assume USDT for now
                    bid=Decimal(str(ticker.bidPrice if hasattr(ticker, 'bidPrice') else 0)),
                    ask=Decimal(str(ticker.askPrice if hasattr(ticker, 'askPrice') else 0)),
                    last=Decimal(str(ticker.lastPrice if hasattr(ticker, 'lastPrice') else 0)),
                    high=Decimal('0'),  # Not provided in BitUnix ticker
                    low=Decimal('0'),   # Not provided in BitUnix ticker
                    volume=Decimal(str(ticker.volume if hasattr(ticker, 'volume') else 0)),
                    quote_volume=Decimal('0'),  # Not provided
                    change=Decimal('0'),  # Calculate if needed
                    change_percent=Decimal('0'),  # Calculate if needed
                    timestamp=datetime.utcnow()
                ))
            except Exception as e:
                logger.error(f"Error parsing ticker: {e}")
        
        return result
    
    async def fetch_ohlcv(self, exchange: str, symbol: str, timeframe: str, limit: int = 100) -> List[Candle]:
        """Fetch OHLCV data"""
        ex = self.get_exchange(exchange)
        
        # Use the async wrapper method
        data = await ex.fetchOHLCV(symbol, timeframe, limit)
        
        # Convert to Candle objects
        candles = []
        for item in data:
            # Convert Unix timestamp to datetime
            from datetime import datetime
            timestamp = datetime.fromtimestamp(item['timestamp'])
            
            candles.append(Candle(
                timestamp=timestamp,
                open=float(item['open']),
                high=float(item['high']),
                low=float(item['low']),
                close=float(item['close']),
                volume=float(item['volume'])
            ))
        
        return candles

    async def fetch_symbol_info(self, exchange: str, symbol: str) -> SymbolInfo:
        """Fetch symbol information"""
        try:
            ex = self.get_exchange(exchange)
            info = await ex.fetchSymbolInfo(symbol)
        except Exception as e:
            logger.error(f"Error fetching symbol info for {symbol} on {exchange}: {e}")
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed for {exchange}. Please check your API keys.")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise Exception(f"Rate limit exceeded on {exchange}. Please try again later.")
            else:
                raise Exception(f"Failed to fetch symbol info: {str(e)}")
        
        return SymbolInfo(
            symbol=symbol,
            base=info.get('baseAsset', ''),
            quote=info.get('quoteAsset', ''),
            active=info.get('active', True),
            type=info.get('type', 'spot'),
            contract_size=Decimal(str(info.get('contractSize', 1))),
            tick_size=Decimal(str(info.get('tickSize', 0.01))),
            lot_size=Decimal(str(info.get('stepSize', 0.001))),
            min_notional=Decimal(str(info.get('minNotional', 10))),
            max_leverage=info.get('maxLeverage', 1),
            maker_fee=Decimal(str(info.get('makerFee', 0.001))),
            taker_fee=Decimal(str(info.get('takerFee', 0.001)))
        )
    
    async def place_order(self, exchange: str, order_request: ExchangeOrderRequest) -> OrderResponse:
        """Place an order"""
        try:
            ex = self.get_exchange(exchange)
            response = await ex.placeOrder(order_request)
        except Exception as e:
            logger.error(f"Error placing order on {exchange}: {e}")
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed for {exchange}. Please check your API keys.")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise Exception(f"Rate limit exceeded on {exchange}. Please try again later.")
            elif "insufficient" in str(e).lower() or "balance" in str(e).lower():
                raise Exception(f"Insufficient balance to place order.")
            else:
                raise Exception(f"Failed to place order: {str(e)}")
        
        # Map exchange status to our status enum
        status_map = {
            'status_active': 'open',
            'active': 'open',
            'new': 'open',
            'partially_filled': 'partially_filled',
            'partial': 'partially_filled',
            'filled': 'filled',
            'done': 'filled',
            'cancelled': 'cancelled',
            'canceled': 'cancelled',
            'rejected': 'rejected',
            'expired': 'expired',
            'pending': 'pending',
            'untriggered': 'pending',
        }
        
        # Map the status
        raw_status = response.status.lower()
        mapped_status = status_map.get(raw_status, 'open')  # Default to 'open' for unknown statuses
        
        return OrderResponse(
            id=response.orderId,
            client_order_id=response.clientId,
            symbol=order_request.symbol,
            side=order_request.side.lower(),
            type=order_request.orderType.lower(),
            status=mapped_status,
            price=response.price,
            average_price=None,  # Not available in ExchangeOrderResponse
            amount=order_request.qty,
            filled=0,  # Not available in ExchangeOrderResponse
            remaining=order_request.qty,  # Not available in ExchangeOrderResponse
            fee=None,  # Not available in ExchangeOrderResponse
            fee_currency=None,  # Not available in ExchangeOrderResponse
            timestamp=response.createTime
        )
    
    async def cancel_order(self, exchange: str, order_id: str, symbol: Optional[str] = None) -> bool:
        """Cancel an order"""
        ex = self.get_exchange(exchange)
        return await ex.cancelOrder(order_id, None, symbol)
    
    async def fetch_orders(self, exchange: str, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Fetch open orders"""
        ex = self.get_exchange(exchange)
        orders = await ex.fetchOrders()
        
        # Map exchange status to our status enum
        status_map = {
            'status_active': 'open',
            'active': 'open',
            'new': 'open',
            'partially_filled': 'partially_filled',
            'partial': 'partially_filled',
            'filled': 'filled',
            'done': 'filled',
            'cancelled': 'cancelled',
            'canceled': 'cancelled',
            'rejected': 'rejected',
            'expired': 'expired',
            'pending': 'pending',
            'untriggered': 'pending',
        }
        
        result = []
        for order in orders:
            # Filter by symbol if provided
            if symbol and order.symbol != symbol:
                continue
            
            # Map the status
            raw_status = order.status.lower()
            mapped_status = status_map.get(raw_status, 'open')  # Default to 'open' for unknown statuses
            
            result.append(OrderResponse(
                id=order.orderId,
                client_order_id=order.clientId,
                symbol=order.symbol,
                side=order.side.lower() if order.side else 'buy',
                type=order.orderType.lower() if order.orderType else 'limit',
                status=mapped_status,
                price=float(order.price) if order.price is not None else 0.0,
                average_price=None,  # Not available in ExchangeOrder
                amount=float(order.qty),
                filled=float(order.executedQty) if order.executedQty is not None else 0.0,
                remaining=float(order.qty) - float(order.executedQty if order.executedQty is not None else 0),
                fee=None,  # Not available in ExchangeOrder
                fee_currency=None,  # Not available in ExchangeOrder
                timestamp=datetime.fromtimestamp(order.createTime / 1000),  # Convert ms to seconds
                updated=None,  # Not available in ExchangeOrder
                # Add TP/SL specific fields
                stop_price=float(order.stopPrice) if hasattr(order, 'stopPrice') and order.stopPrice is not None else None,
                trigger_price=float(order.triggerPrice) if hasattr(order, 'triggerPrice') and order.triggerPrice is not None else None,
                reduce_only=order.reduceOnly if hasattr(order, 'reduceOnly') else None,
                post_only=order.postOnly if hasattr(order, 'postOnly') else None,
                time_in_force=order.timeInForce if hasattr(order, 'timeInForce') else None,
                raw_type=order.rawOrderType if hasattr(order, 'rawOrderType') else None
            ))
        
        return result
    
    async def fetch_positions(self, exchange: str) -> List[Position]:
        """Fetch positions"""
        try:
            ex = self.get_exchange(exchange)
            positions = await ex.fetchPositions()
        except Exception as e:
            logger.error(f"Error fetching positions from {exchange}: {e}")
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed for {exchange}. Please check your API keys.")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise Exception(f"Rate limit exceeded on {exchange}. Please try again later.")
            else:
                raise Exception(f"Failed to fetch positions: {str(e)}")
        
        result = []
        for pos in positions:
            # Determine side from size (negative = short, positive = long)
            # or from raw_response if available
            if hasattr(pos, 'side') and pos.side:
                side = pos.side.lower()
            elif hasattr(pos, 'raw_response') and pos.raw_response and 'side' in pos.raw_response:
                raw_side = pos.raw_response['side']
                side = 'short' if raw_side.upper() == 'SELL' else 'long'
            else:
                # Use size to determine side
                side = 'short' if pos.size < 0 else 'long'
            
            # Extract TP/SL prices from raw response if available
            take_profit_price = None
            stop_loss_price = None
            
            if hasattr(pos, 'raw_response') and pos.raw_response:
                # Check for LMEX format TP/SL orders
                tp_order = pos.raw_response.get('takeProfitOrder')
                if tp_order and isinstance(tp_order, dict):
                    take_profit_price = float(tp_order.get('triggerPrice', 0)) or None
                
                sl_order = pos.raw_response.get('stopLossOrder')
                if sl_order and isinstance(sl_order, dict):
                    stop_loss_price = float(sl_order.get('triggerPrice', 0)) or None
            
            result.append(Position(
                symbol=pos.symbol,
                side=side,
                size=float(abs(pos.size)),
                entry_price=float(pos.entryPrice),
                mark_price=float(pos.markPrice),
                liquidation_price=float(pos.liquidationPrice) if hasattr(pos, 'liquidationPrice') else 0.0,
                unrealized_pnl=float(pos.pnl),  # ExchangePosition has 'pnl' not 'unrealizedPnl'
                realized_pnl=0.0,  # Not available in ExchangePosition
                margin=0.0,  # Not available in ExchangePosition
                leverage=1,  # Not available in ExchangePosition
                percentage=float(pos.pnlPercentage),
                timestamp=datetime.utcnow(),  # Not available in ExchangePosition
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price
            ))
        
        return result
    
    async def fetch_balance(self, exchange: str) -> AccountInfo:
        """Fetch account balance"""
        try:
            ex = self.get_exchange(exchange)
            balance_list = await ex.fetchBalance()
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange}: {e}")
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed for {exchange}. Please check your API keys.")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise Exception(f"Rate limit exceeded on {exchange}. Please try again later.")
            else:
                raise Exception(f"Failed to fetch balance: {str(e)}")
        
        balances = {}
        total_usd = 0.0
        
        # Handle list of ExchangeBalance objects
        for bal in balance_list:
            currency = bal.asset
            balances[currency] = Balance(
                currency=currency,
                free=float(bal.available),
                used=float(bal.locked),
                total=float(bal.balance)
            )
            # Simple USD calculation (would need real rates in production)
            if currency in ['USDT', 'USD']:
                total_usd += float(bal.balance)
        
        return AccountInfo(
            id=f"{exchange}_account",
            type="futures",
            balances=balances,
            total_value_usd=total_usd,
            timestamp=datetime.utcnow()
        )


exchange_manager = ExchangeManager()