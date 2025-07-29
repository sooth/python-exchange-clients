from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
import logging
from decimal import Decimal

from backend.models.trading import CreateOrderRequest, OrderResponse, CancelOrderRequest, Position
from backend.services.exchange_manager import exchange_manager
from backend.core.config import settings
from exchanges.base import ExchangeOrderRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def convert_to_exchange_order(order: CreateOrderRequest, exchange: str) -> ExchangeOrderRequest:
    """Convert API order request to exchange order request"""
    return ExchangeOrderRequest(
        symbol=order.symbol,
        side=order.side.value.upper(),
        orderType=order.type.value.upper(),
        qty=float(order.amount),
        price=float(order.price) if order.price else None,
        stopPrice=float(order.stop_price) if order.stop_price else None,
        timeInForce=order.time_in_force,
        orderLinkId=order.client_order_id
    )


@router.post("/order", response_model=OrderResponse)
async def place_order(
    order: CreateOrderRequest,
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Place a new order"""
    try:
        exchange_order = convert_to_exchange_order(order, exchange)
        return await exchange_manager.place_order(exchange, exchange_order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/order/{order_id}", response_model=dict)
async def cancel_order(
    order_id: str,
    symbol: Optional[str] = Query(default=None, description="Symbol (required for some exchanges)"),
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Cancel an existing order"""
    try:
        success = await exchange_manager.cancel_order(exchange, order_id, symbol)
        if success:
            return {"success": True, "message": f"Order {order_id} cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel order")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orders", response_model=List[OrderResponse])
async def get_open_orders(
    symbol: Optional[str] = Query(default=None, description="Filter by symbol"),
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get all open orders"""
    try:
        return await exchange_manager.fetch_orders(exchange, symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/order/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    symbol: Optional[str] = Query(default=None, description="Symbol (required for some exchanges)"),
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get details of a specific order"""
    try:
        orders = await exchange_manager.fetch_orders(exchange, symbol)
        for order in orders:
            if order.id == order_id:
                return order
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/positions", response_model=List[Position])
async def get_positions(
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get all open positions"""
    try:
        return await exchange_manager.fetch_positions(exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/position/{symbol}", response_model=Position)
async def get_position(
    symbol: str,
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get position for a specific symbol"""
    try:
        positions = await exchange_manager.fetch_positions(exchange)
        for position in positions:
            if position.symbol == symbol:
                return position
        raise HTTPException(status_code=404, detail=f"No position found for {symbol}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")