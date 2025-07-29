from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import uuid
import logging

from backend.ws.manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(default=None)
):
    """WebSocket endpoint for real-time data streaming"""
    if not client_id:
        client_id = str(uuid.uuid4())
    
    await websocket_manager(websocket, client_id)


@router.get("/info")
async def websocket_info():
    """Get WebSocket connection information"""
    return {
        "endpoint": "/api/v1/ws/connect",
        "protocols": ["wss", "ws"],
        "message_types": [
            "subscribe",
            "unsubscribe",
            "ping",
            "pong",
            "ticker",
            "orderbook",
            "trades",
            "orders",
            "positions",
            "balance"
        ],
        "channels": [
            {
                "name": "ticker",
                "description": "Real-time price ticker updates",
                "subscription": {
                    "type": "subscribe",
                    "channel": "ticker",
                    "symbols": ["BTCUSDT", "ETHUSDT"]
                }
            },
            {
                "name": "orderbook",
                "description": "Real-time orderbook updates",
                "subscription": {
                    "type": "subscribe",
                    "channel": "orderbook",
                    "symbols": ["BTCUSDT"]
                }
            },
            {
                "name": "trades",
                "description": "Real-time trade feed",
                "subscription": {
                    "type": "subscribe",
                    "channel": "trades",
                    "symbols": ["BTCUSDT"]
                }
            }
        ]
    }