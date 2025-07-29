"""Grid Calculator - Handles grid level calculations"""

import math
from typing import List, Tuple, Optional
from .types import GridType, GridLevel, OrderSide, GridConfig, PositionDirection


class GridCalculator:
    """Calculates grid levels and order parameters"""
    
    def __init__(self, config: GridConfig):
        self.config = config
        
    def calculate_grid_levels(self, current_price: Optional[float] = None) -> List[GridLevel]:
        """
        Calculate all grid levels based on configuration
        
        Args:
            current_price: Current market price (optional, for optimization)
            
        Returns:
            List of GridLevel objects
        """
        levels = []
        
        if self.config.grid_type == GridType.ARITHMETIC:
            levels = self._calculate_arithmetic_grid()
        else:
            levels = self._calculate_geometric_grid()
        
        # Assign buy/sell sides based on position direction
        levels = self._assign_order_sides(levels, current_price)
        
        # Calculate quantities for each level
        levels = self._calculate_quantities(levels)
        
        return levels
    
    def _calculate_arithmetic_grid(self) -> List[GridLevel]:
        """Calculate arithmetic (linear) grid levels"""
        levels = []
        spacing = (self.config.upper_price - self.config.lower_price) / (self.config.grid_count - 1)
        
        for i in range(self.config.grid_count):
            price = self.config.lower_price + (i * spacing)
            levels.append(GridLevel(
                index=i,
                price=round(price, self._get_price_precision()),
                side=OrderSide.BUY,  # Will be updated later
                quantity=0  # Will be calculated later
            ))
        
        return levels
    
    def _calculate_geometric_grid(self) -> List[GridLevel]:
        """Calculate geometric (percentage-based) grid levels"""
        levels = []
        ratio = (self.config.upper_price / self.config.lower_price) ** (1 / (self.config.grid_count - 1))
        
        for i in range(self.config.grid_count):
            price = self.config.lower_price * (ratio ** i)
            levels.append(GridLevel(
                index=i,
                price=round(price, self._get_price_precision()),
                side=OrderSide.BUY,  # Will be updated later
                quantity=0  # Will be calculated later
            ))
        
        return levels
    
    def _assign_order_sides(self, levels: List[GridLevel], current_price: Optional[float]) -> List[GridLevel]:
        """Assign buy/sell sides to grid levels based on position direction"""
        if not current_price:
            # If no current price, use the midpoint
            current_price = (self.config.upper_price + self.config.lower_price) / 2
        
        for level in levels:
            if self.config.position_direction == PositionDirection.LONG:
                # Long only - all orders below current price are buys
                level.side = OrderSide.BUY if level.price < current_price else OrderSide.SELL
            elif self.config.position_direction == PositionDirection.SHORT:
                # Short only - all orders above current price are sells
                level.side = OrderSide.SELL if level.price > current_price else OrderSide.BUY
            else:  # NEUTRAL
                # Neutral - buys below, sells above
                level.side = OrderSide.BUY if level.price < current_price else OrderSide.SELL
        
        return levels
    
    def _calculate_quantities(self, levels: List[GridLevel]) -> List[GridLevel]:
        """Calculate order quantities for each grid level"""
        investment_per_grid = self.config.investment_per_grid
        
        for level in levels:
            # Calculate base quantity
            if self.config.leverage > 1:
                # With leverage, we can use more buying power
                effective_investment = investment_per_grid * self.config.leverage
            else:
                effective_investment = investment_per_grid
            
            # Calculate quantity based on price
            quantity = effective_investment / level.price
            
            # Round to appropriate precision
            level.quantity = round(quantity, self._get_quantity_precision())
        
        return levels
    
    def get_initial_orders(self, levels: List[GridLevel], current_price: float) -> List[GridLevel]:
        """
        Get the initial orders to place when starting the grid
        
        Args:
            levels: All grid levels
            current_price: Current market price
            
        Returns:
            List of grid levels that should have orders placed
        """
        initial_orders = []
        
        # For grid bots, we want continuous coverage
        # Place orders at all levels except those that would execute immediately
        min_distance = 0.0005  # 0.05% minimum distance from current price
        
        for level in levels:
            # Calculate distance from current price
            price_diff_pct = abs(level.price - current_price) / current_price
            
            # Skip only if too close AND would execute immediately
            if level.side == OrderSide.BUY and level.price > current_price:
                # This is a buy order above market - skip it
                continue
            if level.side == OrderSide.SELL and level.price < current_price:
                # This is a sell order below market - skip it
                continue
            
            # Skip if too close to current price (would likely execute immediately)
            if price_diff_pct < min_distance:
                continue
            
            # Add to initial orders
            initial_orders.append(level)
        
        return initial_orders
    
    def calculate_grid_profit(self, buy_price: float, sell_price: float, quantity: float, fee_rate: float = 0.001) -> Tuple[float, float]:
        """
        Calculate profit from a grid trade
        
        Args:
            buy_price: Buy order price
            sell_price: Sell order price
            quantity: Trade quantity
            fee_rate: Trading fee rate (default 0.1%)
            
        Returns:
            Tuple of (profit, profit_percentage)
        """
        # Calculate gross profit
        gross_profit = (sell_price - buy_price) * quantity
        
        # Calculate fees
        buy_fee = buy_price * quantity * fee_rate
        sell_fee = sell_price * quantity * fee_rate
        total_fees = buy_fee + sell_fee
        
        # Net profit
        net_profit = gross_profit - total_fees
        
        # Profit percentage
        investment = buy_price * quantity
        profit_percentage = (net_profit / investment) * 100 if investment > 0 else 0
        
        return net_profit, profit_percentage
    
    def suggest_grid_parameters(self, current_price: float, volatility: float) -> dict:
        """
        Suggest optimal grid parameters based on market conditions
        
        Args:
            current_price: Current market price
            volatility: Market volatility (e.g., 24h price change percentage)
            
        Returns:
            Dictionary with suggested parameters
        """
        # Base suggestions on volatility
        if volatility < 5:
            # Low volatility - tighter grid
            price_range_pct = 5
            grid_count = 20
        elif volatility < 10:
            # Medium volatility
            price_range_pct = 10
            grid_count = 30
        else:
            # High volatility - wider grid
            price_range_pct = 20
            grid_count = 50
        
        # Calculate price range
        lower_price = current_price * (1 - price_range_pct / 200)
        upper_price = current_price * (1 + price_range_pct / 200)
        
        return {
            'lower_price': round(lower_price, self._get_price_precision()),
            'upper_price': round(upper_price, self._get_price_precision()),
            'grid_count': grid_count,
            'grid_type': GridType.GEOMETRIC if volatility > 10 else GridType.ARITHMETIC
        }
    
    def recalculate_grid_on_price_move(self, levels: List[GridLevel], current_price: float) -> Optional[List[GridLevel]]:
        """
        Recalculate grid if price moves significantly outside range
        
        Args:
            levels: Current grid levels
            current_price: Current market price
            
        Returns:
            New grid levels if recalculation is needed, None otherwise
        """
        # Check if price is outside grid range
        price_above = current_price > self.config.upper_price * 1.05
        price_below = current_price < self.config.lower_price * 0.95
        
        if not (price_above or price_below):
            return None
        
        # Calculate new range centered on current price
        range_size = self.config.upper_price - self.config.lower_price
        
        if self.config.trailing_up and price_above:
            # Trail up - shift grid upward
            self.config.lower_price = current_price - (range_size * 0.4)
            self.config.upper_price = current_price + (range_size * 0.6)
        elif self.config.trailing_down and price_below:
            # Trail down - shift grid downward  
            self.config.lower_price = current_price - (range_size * 0.6)
            self.config.upper_price = current_price + (range_size * 0.4)
        else:
            # No trailing enabled
            return None
        
        # Recalculate grid levels
        return self.calculate_grid_levels(current_price)
    
    def _get_price_precision(self) -> int:
        """Get price precision for the symbol"""
        # This should be obtained from exchange symbol info
        # For now, use a default
        return 2
    
    def _get_quantity_precision(self) -> int:
        """Get quantity precision for the symbol"""
        # This should be obtained from exchange symbol info
        # For now, use a default
        return 3