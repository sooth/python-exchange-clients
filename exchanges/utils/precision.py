"""Symbol Precision Manager for Exchange Clients"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


class SymbolPrecisionManager:
    """
    Manages symbol precision data for exchanges to ensure accurate order formatting
    """
    _instances = {}  # One instance per exchange
    
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.precision_cache: Dict[str, Dict[str, Any]] = {}
        self.last_update: Optional[datetime] = None
        self.cache_duration_hours = 24
        self.cache_file = f"{exchange_name.lower()}_precision_cache.json"
        # Try to find cache file in utils directory
        self.cache_path = os.path.join(os.path.dirname(__file__), self.cache_file)
        # Load cached data on initialization
        self._load_cache()
    
    @classmethod
    def get_instance(cls, exchange_name: str = "default"):
        """Get or create instance for specific exchange"""
        if exchange_name not in cls._instances:
            cls._instances[exchange_name] = cls(exchange_name)
        return cls._instances[exchange_name]
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get all precision info for a symbol"""
        if self._needs_refresh():
            self._fetch_all_symbols()
        return self.precision_cache.get(symbol, {})
    
    def get_price_precision(self, symbol: str) -> int:
        """Get price decimal precision for a symbol"""
        info = self.get_symbol_info(symbol)
        
        # Check for direct precision field first (BitUnix uses quotePrecision)
        if "quotePrecision" in info:
            return int(info["quotePrecision"])
        
        # Check for other direct precision fields
        if "pricePrecision" in info:
            return int(info["pricePrecision"])
        
        tick_size = info.get("tick_size", info.get("minPrice", 0.01))
        
        # Convert tick size to precision (e.g., 0.01 -> 2, 0.001 -> 3)
        if tick_size == 0:
            return 2  # Default
        
        # Count decimal places
        tick_str = f"{tick_size:.10f}".rstrip('0')
        if '.' in tick_str:
            return len(tick_str.split('.')[1])
        return 0
    
    def get_quantity_precision(self, symbol: str) -> int:
        """Get quantity decimal precision for a symbol"""
        info = self.get_symbol_info(symbol)
        
        # Check for direct precision field first (BitUnix uses basePrecision)
        if "basePrecision" in info:
            return int(info["basePrecision"])
        
        # Check for other direct precision fields
        if "quantityPrecision" in info:
            return int(info["quantityPrecision"])
        
        # Try different field names used by exchanges
        min_qty = info.get("min_qty", info.get("minQty", info.get("min_order_size", 1)))
        
        # Convert min quantity to precision
        if min_qty == 0:
            return 0
        
        # For values >= 1, precision is 0
        if min_qty >= 1:
            return 0
        
        # Count decimal places for fractional values
        qty_str = f"{min_qty:.10f}".rstrip('0')
        if '.' in qty_str:
            return len(qty_str.split('.')[1])
        return 0
    
    def get_min_quantity(self, symbol: str) -> float:
        """Get minimum order quantity for a symbol"""
        info = self.get_symbol_info(symbol)
        return float(info.get("min_qty", info.get("minQty", info.get("min_order_size", 1))))
    
    def get_max_quantity(self, symbol: str) -> float:
        """Get maximum order quantity for a symbol"""
        info = self.get_symbol_info(symbol)
        return float(info.get("max_qty", info.get("maxQty", info.get("max_order_size", 1000000))))
    
    def is_symbol_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported"""
        if self._needs_refresh():
            self._fetch_all_symbols()
        return symbol in self.precision_cache
    
    def get_contract_size(self, symbol: str) -> float:
        """Get contract size for a symbol"""
        symbol_info = self.get_symbol_info(symbol)
        contract_size = symbol_info.get("contract_size")
        
        if contract_size is None:
            raise ValueError(f"Contract size not found for {symbol}. Please ensure fetchTickers() has been called to populate symbol data.")
        
        return float(contract_size)
    
    def get_min_trade_volume(self, symbol: str) -> float:
        """Get minimum trade volume/quantity for a symbol"""
        info = self.get_symbol_info(symbol)
        # Support multiple field names used by different exchanges
        min_vol = info.get("min_trade_volume", 
                          info.get("minTradeVolume",  # BitUnix format
                          info.get("minQty", 0.001)))
        return float(min_vol)
    
    def _needs_refresh(self) -> bool:
        """Check if cache needs refreshing - only on first init when cache is empty"""
        # Only fetch fresh data if we have no cached data at all
        return len(self.precision_cache) == 0
    
    def _fetch_all_symbols(self):
        """Fetch all symbol precision data from exchange API"""
        # This should be overridden by exchange-specific implementations
        # or called by the exchange after fetching tickers
        pass
    
    def _load_cache(self):
        """Load precision data from cache file"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r') as f:
                    data = json.load(f)
                    # Support both formats: 'symbols' and 'precision_cache' (BitUnix format)
                    self.precision_cache = data.get('symbols', data.get('precision_cache', {}))
                    
                    # Parse the update timestamp
                    update_str = data.get('last_update')
                    if update_str:
                        self.last_update = datetime.fromisoformat(update_str)
                    
                    print(f"DEBUG: Loaded precision cache with {len(self.precision_cache)} symbols from {self.cache_file}")
        except Exception as e:
            print(f"DEBUG: Error loading precision cache: {e}")
            self.precision_cache = {}
    
    def _save_cache(self):
        """Save precision data to cache file"""
        try:
            data = {
                'last_update': datetime.now().isoformat(),
                'symbols': self.precision_cache
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"DEBUG: Saved precision cache with {len(self.precision_cache)} symbols to {self.cache_file}")
        except Exception as e:
            print(f"DEBUG: Error saving precision cache: {e}")
    
    def update_symbol_info(self, symbol: str, info: Dict[str, Any]):
        """Update precision info for a specific symbol"""
        self.precision_cache[symbol] = info
        self.last_update = datetime.now()