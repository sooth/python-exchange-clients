"""Grid Bot Type Definitions"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import time


class GridType(Enum):
    """Grid spacing type"""
    ARITHMETIC = "arithmetic"  # Equal price intervals
    GEOMETRIC = "geometric"    # Percentage-based intervals


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class GridState(Enum):
    """Grid bot state"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PositionDirection(Enum):
    """Position direction for grid bot"""
    LONG = "LONG"     # Long-only grid
    SHORT = "SHORT"   # Short-only grid
    NEUTRAL = "NEUTRAL"  # Both directions


@dataclass
class GridLevel:
    """Represents a single grid level"""
    index: int
    price: float
    side: OrderSide
    quantity: float
    order_id: Optional[str] = None
    status: str = "pending"  # pending, placed, filled, cancelled
    filled_at: Optional[float] = None
    
    def is_active(self) -> bool:
        """Check if this level has an active order"""
        return self.status == "placed" and self.order_id is not None


@dataclass
class GridOrder:
    """Grid order information"""
    grid_index: int
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    price: float
    quantity: float
    status: str
    created_at: float
    filled_at: Optional[float] = None
    fill_price: Optional[float] = None
    commission: Optional[float] = None


@dataclass
class GridTrade:
    """Completed grid trade (buy + sell pair)"""
    buy_order: GridOrder
    sell_order: GridOrder
    profit: float
    profit_percentage: float
    completed_at: float


@dataclass
class GridPosition:
    """Current position information"""
    symbol: str
    size: float  # Positive for long, negative for short
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    total_trades: int
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL percentage"""
        if self.entry_price == 0:
            return 0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100


@dataclass
class GridStats:
    """Grid bot statistics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_volume: float = 0
    grid_profit: float = 0  # Profit from grid trades
    position_profit: float = 0  # Unrealized position profit
    total_profit: float = 0  # Total profit
    fees_paid: float = 0
    uptime_seconds: float = 0
    roi: float = 0
    win_rate: float = 0
    average_profit_per_trade: float = 0
    max_drawdown: float = 0
    current_drawdown: float = 0
    
    def update_metrics(self):
        """Update calculated metrics"""
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            self.average_profit_per_trade = self.grid_profit / self.total_trades
        self.total_profit = self.grid_profit + self.position_profit


@dataclass
class GridConfig:
    """Grid bot configuration"""
    # Basic settings
    symbol: str
    grid_type: GridType
    position_direction: PositionDirection
    
    # Price range
    upper_price: float
    lower_price: float
    
    # Grid settings
    grid_count: int
    total_investment: float
    
    # Position settings
    leverage: int = 1
    position_mode: str = "one-way"  # one-way, hedge
    margin_mode: str = "cross"  # cross, isolated
    
    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_position_size: Optional[float] = None
    max_drawdown_percentage: Optional[float] = None
    
    # Order settings
    order_type: str = "LIMIT"
    time_in_force: str = "GTC"
    post_only: bool = True
    
    # Behavior settings
    auto_restart: bool = True
    trailing_up: bool = False
    trailing_down: bool = False
    cancel_orders_on_stop: bool = True
    close_position_on_stop: bool = False
    
    # Performance settings
    min_profit_per_grid: Optional[float] = None
    rebalance_threshold: Optional[float] = None
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if self.upper_price <= self.lower_price:
            errors.append("Upper price must be greater than lower price")
        
        if self.grid_count < 2:
            errors.append("Grid count must be at least 2")
        
        if self.total_investment <= 0:
            errors.append("Total investment must be positive")
        
        if self.leverage < 1 or self.leverage > 125:
            errors.append("Leverage must be between 1 and 125")
        
        if self.stop_loss:
            if self.position_direction == PositionDirection.LONG and self.stop_loss >= self.lower_price:
                errors.append("Stop loss must be below lower price for long grids")
            elif self.position_direction == PositionDirection.SHORT and self.stop_loss <= self.upper_price:
                errors.append("Stop loss must be above upper price for short grids")
        
        return errors
    
    @property
    def price_range(self) -> float:
        """Get the price range"""
        return self.upper_price - self.lower_price
    
    @property
    def grid_spacing(self) -> float:
        """Get the grid spacing"""
        if self.grid_type == GridType.ARITHMETIC:
            return self.price_range / (self.grid_count - 1)
        else:  # Geometric
            return ((self.upper_price / self.lower_price) ** (1 / (self.grid_count - 1)) - 1) * 100
    
    @property
    def investment_per_grid(self) -> float:
        """Get investment per grid level"""
        # Reserve some for fees and slippage
        usable_investment = self.total_investment * 0.98
        return usable_investment / self.grid_count