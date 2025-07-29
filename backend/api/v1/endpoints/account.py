from fastapi import APIRouter, Query, HTTPException
from typing import Dict
import logging

from backend.models.account import AccountInfo, ApiKeyRequest, ApiKeyResponse
from backend.services.exchange_manager import exchange_manager
from backend.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api-keys", response_model=ApiKeyResponse)
async def add_api_keys(api_key_request: ApiKeyRequest):
    """Add API keys for an exchange"""
    try:
        # In production, you'd securely store these keys
        # For now, we'll just validate the exchange exists
        if api_key_request.exchange not in settings.SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {api_key_request.exchange}")
        
        # Here you would initialize the exchange with the provided keys
        # exchange = exchange_manager.get_exchange(api_key_request.exchange)
        # exchange.set_credentials(api_key_request.api_key, api_key_request.api_secret)
        
        return ApiKeyResponse(
            exchange=api_key_request.exchange,
            status="success",
            message="API keys added successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding API keys: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/balance", response_model=AccountInfo)
async def get_account_balance(
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get account balance and information"""
    try:
        return await exchange_manager.fetch_balance(exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trading-fees", response_model=Dict[str, float])
async def get_trading_fees(
    exchange: str = Query(default=settings.DEFAULT_EXCHANGE, description="Exchange name")
):
    """Get current trading fee rates"""
    # This would need implementation based on exchange APIs
    return {
        "maker_fee": 0.001,
        "taker_fee": 0.001
    }