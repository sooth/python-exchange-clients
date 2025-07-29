"""Initial Position Calculator for Grid Bot"""

from typing import List, Tuple, Optional
from .types import GridLevel, OrderSide, GridConfig, PositionDirection


class InitialPositionCalculator:
    """Calculates the initial position needed when starting a grid bot"""
    
    def __init__(self, config: GridConfig):
        self.config = config
    
    def calculate_initial_position(self, grid_levels: List[GridLevel], current_price: float) -> Tuple[float, OrderSide, List[int]]:
        """
        Calculate the initial position to open when starting the grid bot.
        
        For LONG grids:
        - Buy the sum of all grid levels ABOVE current price
        - This ensures we have inventory to sell as price rises
        
        For SHORT grids:
        - Sell the sum of all grid levels BELOW current price
        - This ensures we have short positions to buy back as price falls
        
        For NEUTRAL grids:
        - Open positions for grid levels on the opposite side of current price
        
        Args:
            grid_levels: List of all grid levels
            current_price: Current market price
            
        Returns:
            Tuple of (total_quantity, side, affected_grid_indices)
        """
        total_quantity = 0.0
        affected_indices = []
        
        if self.config.position_direction == PositionDirection.LONG:
            # LONG: Buy all grids ABOVE current price
            side = OrderSide.BUY
            for level in grid_levels:
                if level.price > current_price:
                    total_quantity += level.quantity
                    affected_indices.append(level.index)
                    
        elif self.config.position_direction == PositionDirection.SHORT:
            # SHORT: Sell all grids BELOW current price
            side = OrderSide.SELL
            for level in grid_levels:
                if level.price < current_price:
                    total_quantity += level.quantity
                    affected_indices.append(level.index)
                    
        else:  # NEUTRAL
            # For neutral, we need to determine which side has more grids
            above_count = sum(1 for level in grid_levels if level.price > current_price)
            below_count = sum(1 for level in grid_levels if level.price < current_price)
            
            if above_count > below_count:
                # More grids above, so buy those
                side = OrderSide.BUY
                for level in grid_levels:
                    if level.price > current_price:
                        total_quantity += level.quantity
                        affected_indices.append(level.index)
            else:
                # More grids below, so sell those
                side = OrderSide.SELL
                for level in grid_levels:
                    if level.price < current_price:
                        total_quantity += level.quantity
                        affected_indices.append(level.index)
        
        return total_quantity, side, affected_indices
    
    def calculate_position_percentage(self, current_price: float) -> float:
        """
        Calculate what percentage of maximum position we should have based on price location.
        
        For LONG:
        - 0% at bottom (all inventory available to buy)
        - 100% at top (fully invested)
        
        For SHORT:
        - 100% at top (fully short)
        - 0% at bottom (all shorts closed)
        
        Args:
            current_price: Current market price
            
        Returns:
            Percentage of maximum position (0-100)
        """
        price_range = self.config.upper_price - self.config.lower_price
        price_position = (current_price - self.config.lower_price) / price_range
        
        # Clamp between 0 and 1
        price_position = max(0, min(1, price_position))
        
        if self.config.position_direction == PositionDirection.LONG:
            # LONG: Higher price = higher position
            return price_position * 100
        elif self.config.position_direction == PositionDirection.SHORT:
            # SHORT: Higher price = higher short position (inverted)
            return (1 - price_position) * 100
        else:
            # NEUTRAL: Always 50%
            return 50.0
    
    def estimate_initial_investment(self, grid_levels: List[GridLevel], current_price: float) -> float:
        """
        Estimate the USDT value needed for the initial position.
        
        Args:
            grid_levels: List of all grid levels
            current_price: Current market price
            
        Returns:
            Estimated USDT value for initial position
        """
        quantity, side, indices = self.calculate_initial_position(grid_levels, current_price)
        
        # Use current price as estimate for market order
        return quantity * current_price
    
    def get_initial_position_summary(self, grid_levels: List[GridLevel], current_price: float) -> dict:
        """
        Get a detailed summary of the initial position calculation.
        
        Args:
            grid_levels: List of all grid levels
            current_price: Current market price
            
        Returns:
            Dictionary with position details
        """
        quantity, side, indices = self.calculate_initial_position(grid_levels, current_price)
        position_pct = self.calculate_position_percentage(current_price)
        investment = self.estimate_initial_investment(grid_levels, current_price)
        
        # Calculate where price is in the range
        price_range = self.config.upper_price - self.config.lower_price
        price_location = ((current_price - self.config.lower_price) / price_range) * 100
        
        return {
            'position_direction': self.config.position_direction.value,
            'current_price': current_price,
            'price_location_pct': price_location,
            'initial_side': side.value,
            'initial_quantity': quantity,
            'initial_investment': investment,
            'affected_grid_levels': len(indices),
            'position_percentage': position_pct,
            'explanation': self._get_explanation(side, quantity, indices, current_price)
        }
    
    def _get_explanation(self, side: OrderSide, quantity: float, indices: List[int], current_price: float) -> str:
        """Generate human-readable explanation of the initial position"""
        if quantity == 0:
            return "No initial position needed - price is at the edge of the range"
        
        direction = self.config.position_direction.value
        
        if direction == "LONG":
            return f"Opening LONG position by buying {quantity:.3f} units at market price ~${current_price:.2f} to fill {len(indices)} grid levels above current price"
        elif direction == "SHORT":
            return f"Opening SHORT position by selling {quantity:.3f} units at market price ~${current_price:.2f} to establish shorts for {len(indices)} grid levels below current price"
        else:
            side_str = "buying" if side == OrderSide.BUY else "selling"
            return f"Opening NEUTRAL position by {side_str} {quantity:.3f} units at market price ~${current_price:.2f} to balance {len(indices)} grid levels"