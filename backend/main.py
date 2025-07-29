from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import datetime
from typing import Any
import json
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings
from backend.api.v1 import api_router
from backend.ws.manager import websocket_manager
# Import exchange_manager will be done in lifespan to avoid circular imports


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Unified Exchange Trading Platform...")
    
    # Import here to avoid circular imports
    from backend.services.exchange_manager import exchange_manager
    
    # Initialize exchanges
    try:
        await exchange_manager.initialize()
        
        # Test connectivity for each exchange
        exchanges = await exchange_manager.get_connected_exchanges()
        logger.info(f"Connected exchanges: {exchanges}")
        
        for exchange in exchanges:
            try:
                # Try to fetch tickers as a connectivity test
                tickers = await exchange_manager.fetch_all_tickers(exchange)
                logger.info(f"✅ {exchange}: Connected successfully, {len(tickers)} trading pairs available")
            except Exception as e:
                logger.warning(f"⚠️ {exchange}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Failed to initialize exchanges: {e}")
        # Continue startup even if exchanges fail - app can still work in demo mode
    
    await websocket_manager.start()
    
    yield
    
    logger.info("Shutting down...")
    await websocket_manager.stop()
    await exchange_manager.cleanup()


# Custom JSON encoder for handling Decimal and datetime
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Custom JSON response that uses our encoder
class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    default_response_class=CustomJSONResponse
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# WebSocket routes are included in the API router


@app.get("/")
async def root():
    return {
        "message": "Unified Exchange Trading Platform API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
async def health_check():
    # Import here to avoid circular imports
    from backend.services.exchange_manager import exchange_manager
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "exchanges": await exchange_manager.get_connected_exchanges()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )