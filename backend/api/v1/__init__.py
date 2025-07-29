from fastapi import APIRouter
from .endpoints import market, trading, account, websocket

api_router = APIRouter()

api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])