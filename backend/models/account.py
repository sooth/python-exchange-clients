from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from decimal import Decimal


class Balance(BaseModel):
    currency: str
    free: float
    used: float
    total: float


class AccountInfo(BaseModel):
    id: str
    type: str  # spot, futures, margin
    balances: Dict[str, Balance]
    total_value_usd: Optional[float] = None
    margin_level: Optional[float] = None
    leverage: Optional[int] = None
    timestamp: datetime


class ApiKeyRequest(BaseModel):
    exchange: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    testnet: bool = False


class ApiKeyResponse(BaseModel):
    exchange: str
    status: str
    message: Optional[str] = None