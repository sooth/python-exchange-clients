import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
from fastapi import WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.websockets import WebSocketState
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.config import settings
from backend.models.websocket import WSMessage, WSMessageType, WSSubscription, WSError
from backend.ws.rate_limiter import UpdateRateLimiter
# Import will be done at runtime to avoid circular imports
try:
    from exchanges.bitunix import BitUnixWebSocketManager
    from exchanges.base import WebSocketChannels
except ImportError:
    # Fallback imports for development
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, parent_dir)
    from exchanges.bitunix import BitUnixWebSocketManager
    from exchanges.base import WebSocketChannels

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        self.exchange_ws_managers: Dict[str, Any] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        # Rate limiter to prevent system overload (max 10 updates per second per symbol)
        self.rate_limiter = UpdateRateLimiter(max_updates_per_second=10)
    
    async def start(self):
        """Start the WebSocket manager"""
        self._running = True
        logger.info("WebSocket manager started")
    
    async def stop(self):
        """Stop the WebSocket manager"""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Disconnect all clients
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
        
        # Stop exchange WebSocket managers
        for ws_manager in self.exchange_ws_managers.values():
            if hasattr(ws_manager, 'disconnect'):
                # disconnect is synchronous, not async
                ws_manager.disconnect()
        
        # Shutdown rate limiter
        await self.rate_limiter.shutdown()
        
        logger.info("WebSocket manager stopped")
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        
        # Send welcome message
        await self.send_message(client_id, WSMessage(
            type=WSMessageType.INFO,
            data={"message": "Connected to Unified Exchange Trading Platform", "client_id": client_id}
        ))
        
        logger.info(f"Client {client_id} connected")
    
    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
            
            del self.active_connections[client_id]
            del self.subscriptions[client_id]
            
            logger.info(f"Client {client_id} disconnected")
    
    async def send_message(self, client_id: str, message: WSMessage):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message.model_dump(mode='json'))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self.disconnect(client_id)
    
    async def broadcast(self, message: WSMessage, channel: Optional[str] = None):
        """Broadcast a message to all clients or those subscribed to a channel"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            if channel is None or channel in self.subscriptions.get(client_id, set()):
                try:
                    await websocket.send_json(message.model_dump(mode='json'))
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def handle_subscription(self, client_id: str, subscription: WSSubscription):
        """Handle subscription request from a client"""
        try:
            exchange = settings.DEFAULT_EXCHANGE
            channel_key = f"{exchange}:{subscription.channel}:{','.join(subscription.symbols)}"
            
            if subscription.type == WSMessageType.SUBSCRIBE:
                self.subscriptions[client_id].add(channel_key)
                
                # Initialize exchange WebSocket if needed
                if exchange not in self.exchange_ws_managers:
                    await self._init_exchange_websocket(exchange)
                
                # Subscribe to exchange data
                ws_manager = self.exchange_ws_managers.get(exchange)
                if ws_manager:
                    for symbol in subscription.symbols:
                        # These methods are synchronous, not async
                        if subscription.channel == "ticker":
                            ws_manager.subscribe_ticker(symbol)
                        elif subscription.channel == "orderbook":
                            ws_manager.subscribe_orderbook(symbol)
                        elif subscription.channel == "trades":
                            ws_manager.subscribe_trades(symbol)
                
                await self.send_message(client_id, WSMessage(
                    type=WSMessageType.INFO,
                    data={"message": f"Subscribed to {channel_key}"}
                ))
                
            elif subscription.type == WSMessageType.UNSUBSCRIBE:
                self.subscriptions[client_id].discard(channel_key)
                
                await self.send_message(client_id, WSMessage(
                    type=WSMessageType.INFO,
                    data={"message": f"Unsubscribed from {channel_key}"}
                ))
                
        except Exception as e:
            logger.error(f"Error handling subscription: {e}")
            await self.send_message(client_id, WSMessage(
                type=WSMessageType.ERROR,
                data=WSError(code=400, message=str(e)).model_dump()
            ))
    
    async def _init_exchange_websocket(self, exchange: str):
        """Initialize WebSocket connection for an exchange"""
        # Import at runtime to avoid circular imports
        from backend.services.exchange_manager import exchange_manager
        
        try:
            if exchange == "bitunix":
                ws_manager = BitUnixWebSocketManager()
                # connect_public is synchronous, not async
                ws_manager.connect_public()
                
                # Set up callbacks with rate limiting
                # This prevents system overload from high-frequency updates
                loop = asyncio.get_event_loop()
                
                def ticker_callback(data):
                    symbol = data.get('symbol', 'unknown')
                    key = f"ticker:{exchange}:{symbol}"
                    asyncio.run_coroutine_threadsafe(
                        self.rate_limiter.process_update(
                            key, self._handle_ticker_update, exchange, data
                        ), 
                        loop
                    )
                
                def orderbook_callback(data):
                    symbol = data.get('symbol', 'unknown')
                    key = f"orderbook:{exchange}:{symbol}"
                    asyncio.run_coroutine_threadsafe(
                        self.rate_limiter.process_update(
                            key, self._handle_orderbook_update, exchange, data
                        ),
                        loop
                    )
                
                def trade_callback(data):
                    symbol = data.get('symbol', 'unknown')
                    key = f"trade:{exchange}:{symbol}"
                    asyncio.run_coroutine_threadsafe(
                        self.rate_limiter.process_update(
                            key, self._handle_trade_update, exchange, data
                        ),
                        loop
                    )
                
                ws_manager.on_ticker = ticker_callback
                ws_manager.on_orderbook = orderbook_callback
                ws_manager.on_trade = trade_callback
                
                self.exchange_ws_managers[exchange] = ws_manager
                logger.info(f"Initialized WebSocket for {exchange}")
                
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket for {exchange}: {e}")
    
    async def _handle_ticker_update(self, exchange: str, data: dict):
        """Handle ticker update from exchange"""
        symbol = data.get('symbol')
        if symbol:
            channel_key = f"{exchange}:ticker:{symbol}"
            message = WSMessage(
                type=WSMessageType.TICKER,
                channel="ticker",
                symbol=symbol,
                data=data
            )
            await self.broadcast(message, channel_key)
    
    async def _handle_orderbook_update(self, exchange: str, data: dict):
        """Handle orderbook update from exchange"""
        symbol = data.get('symbol')
        if symbol:
            channel_key = f"{exchange}:orderbook:{symbol}"
            message = WSMessage(
                type=WSMessageType.ORDERBOOK,
                channel="orderbook",
                symbol=symbol,
                data=data
            )
            await self.broadcast(message, channel_key)
    
    async def _handle_trade_update(self, exchange: str, data: dict):
        """Handle trade update from exchange"""
        symbol = data.get('symbol')
        if symbol:
            channel_key = f"{exchange}:trades:{symbol}"
            message = WSMessage(
                type=WSMessageType.TRADES,
                channel="trades",
                symbol=symbol,
                data=data
            )
            await self.broadcast(message, channel_key)
    
    async def handle_client_message(self, client_id: str, message: dict):
        """Handle incoming message from a client"""
        try:
            msg_type = message.get('type')
            
            if msg_type == WSMessageType.PING.value:
                await self.send_message(client_id, WSMessage(type=WSMessageType.PONG))
                
            elif msg_type == WSMessageType.SUBSCRIBE.value:
                subscription = WSSubscription(**message)
                await self.handle_subscription(client_id, subscription)
                
            elif msg_type == WSMessageType.UNSUBSCRIBE.value:
                subscription = WSSubscription(**message)
                await self.handle_subscription(client_id, subscription)
                
            else:
                await self.send_message(client_id, WSMessage(
                    type=WSMessageType.ERROR,
                    data=WSError(code=400, message=f"Unknown message type: {msg_type}").model_dump()
                ))
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await self.send_message(client_id, WSMessage(
                type=WSMessageType.ERROR,
                data=WSError(code=500, message=str(e)).model_dump()
            ))


class WebSocketApp:
    def __init__(self):
        self.manager = ConnectionManager()
    
    async def start(self):
        await self.manager.start()
    
    async def stop(self):
        await self.manager.stop()
    
    async def __call__(self, websocket: WebSocket, client_id: str):
        await self.manager.connect(websocket, client_id)
        try:
            while True:
                data = await websocket.receive_json()
                await self.manager.handle_client_message(client_id, data)
        except WebSocketDisconnect:
            await self.manager.disconnect(client_id)
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
            await self.manager.disconnect(client_id)


websocket_manager = WebSocketApp()