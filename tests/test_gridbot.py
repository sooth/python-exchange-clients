"""Grid Bot Test Suite"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gridbot.types import GridConfig, GridType, PositionDirection, GridLevel, OrderSide
from gridbot.calculator import GridCalculator
from gridbot.config import GridBotConfig


class TestGridCalculator(unittest.TestCase):
    """Test grid calculator functionality"""
    
    def setUp(self):
        """Set up test configuration"""
        self.config = GridConfig(
            symbol="BTCUSDT",
            grid_type=GridType.ARITHMETIC,
            position_direction=PositionDirection.NEUTRAL,
            upper_price=45000,
            lower_price=42000,
            grid_count=10,
            total_investment=1000,
            leverage=1
        )
        self.calculator = GridCalculator(self.config)
    
    def test_arithmetic_grid_calculation(self):
        """Test arithmetic grid level calculation"""
        levels = self.calculator._calculate_arithmetic_grid()
        
        # Check number of levels
        self.assertEqual(len(levels), 10)
        
        # Check price range
        self.assertEqual(levels[0].price, 42000)
        self.assertEqual(levels[-1].price, 45000)
        
        # Check equal spacing
        spacing = (45000 - 42000) / 9  # 9 intervals for 10 levels
        for i in range(1, len(levels)):
            diff = levels[i].price - levels[i-1].price
            self.assertAlmostEqual(diff, spacing, delta=1)
    
    def test_geometric_grid_calculation(self):
        """Test geometric grid level calculation"""
        self.config.grid_type = GridType.GEOMETRIC
        calculator = GridCalculator(self.config)
        levels = calculator._calculate_geometric_grid()
        
        # Check number of levels
        self.assertEqual(len(levels), 10)
        
        # Check price range
        self.assertEqual(levels[0].price, 42000)
        self.assertAlmostEqual(levels[-1].price, 45000, places=0)
        
        # Check percentage-based spacing
        for i in range(1, len(levels)):
            ratio = levels[i].price / levels[i-1].price
            # Check ratio is consistent (geometric progression)
            expected_ratio = (45000 / 42000) ** (1 / 9)
            self.assertAlmostEqual(ratio, expected_ratio, places=4)
    
    def test_order_side_assignment(self):
        """Test buy/sell side assignment"""
        levels = self.calculator.calculate_grid_levels(current_price=43500)
        
        # Check orders below current price are buys
        for level in levels:
            if level.price < 43500:
                self.assertEqual(level.side, OrderSide.BUY)
            else:
                self.assertEqual(level.side, OrderSide.SELL)
    
    def test_quantity_calculation(self):
        """Test order quantity calculation"""
        levels = self.calculator.calculate_grid_levels()
        
        # Check all levels have quantities
        for level in levels:
            self.assertGreater(level.quantity, 0)
        
        # Check investment per grid
        expected_investment = self.config.investment_per_grid
        for level in levels:
            actual_investment = level.price * level.quantity
            # Investment should be close to expected (with some variance due to rounding)
            self.assertAlmostEqual(actual_investment, expected_investment, delta=expected_investment * 0.2)
    
    def test_grid_profit_calculation(self):
        """Test profit calculation for grid trades"""
        buy_price = 42000
        sell_price = 42500
        quantity = 0.01
        
        profit, profit_pct = self.calculator.calculate_grid_profit(
            buy_price, sell_price, quantity
        )
        
        # Expected: (42500 - 42000) * 0.01 - fees
        gross_profit = 5.0
        fees = (420 + 425) * 0.001  # 0.1% fee on both sides
        expected_profit = gross_profit - fees
        
        self.assertAlmostEqual(profit, expected_profit, places=2)
        self.assertGreater(profit_pct, 0)
    
    def test_grid_parameter_suggestion(self):
        """Test automatic parameter suggestion"""
        # Low volatility
        params = self.calculator.suggest_grid_parameters(43000, volatility=3)
        self.assertLess(params['upper_price'] - params['lower_price'], 3000)
        self.assertEqual(params['grid_count'], 20)
        
        # High volatility
        params = self.calculator.suggest_grid_parameters(43000, volatility=15)
        self.assertGreater(params['upper_price'] - params['lower_price'], 5000)
        self.assertEqual(params['grid_count'], 50)


class TestGridConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config
        config = GridConfig(
            symbol="BTCUSDT",
            grid_type=GridType.ARITHMETIC,
            position_direction=PositionDirection.NEUTRAL,
            upper_price=45000,
            lower_price=42000,
            grid_count=20,
            total_investment=1000
        )
        errors = config.validate()
        self.assertEqual(len(errors), 0)
        
        # Invalid price range
        config.upper_price = 40000
        errors = config.validate()
        self.assertIn("Upper price must be greater than lower price", errors)
        
        # Invalid grid count
        config.upper_price = 45000
        config.grid_count = 1
        errors = config.validate()
        self.assertIn("Grid count must be at least 2", errors)
        
        # Invalid investment
        config.grid_count = 20
        config.total_investment = -100
        errors = config.validate()
        self.assertIn("Total investment must be positive", errors)
    
    def test_config_properties(self):
        """Test configuration calculated properties"""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_type=GridType.ARITHMETIC,
            position_direction=PositionDirection.NEUTRAL,
            upper_price=45000,
            lower_price=42000,
            grid_count=10,
            total_investment=1000
        )
        
        # Test price range
        self.assertEqual(config.price_range, 3000)
        
        # Test grid spacing
        self.assertAlmostEqual(config.grid_spacing, 333.33, places=2)
        
        # Test investment per grid
        self.assertAlmostEqual(config.investment_per_grid, 98, places=0)
    
    def test_config_serialization(self):
        """Test configuration save/load"""
        config_manager = GridBotConfig()
        
        # Create config
        original = config_manager.create_default_config("BTCUSDT")
        original.upper_price = 45000
        original.lower_price = 42000
        
        # Convert to dict and back
        data = config_manager.to_dict(original)
        loaded = config_manager.from_dict(data)
        
        # Verify fields match
        self.assertEqual(loaded.symbol, original.symbol)
        self.assertEqual(loaded.upper_price, original.upper_price)
        self.assertEqual(loaded.lower_price, original.lower_price)
        self.assertEqual(loaded.grid_type, original.grid_type)


class TestGridLevels(unittest.TestCase):
    """Test grid level functionality"""
    
    def test_grid_level_active_check(self):
        """Test grid level active status"""
        level = GridLevel(
            index=0,
            price=42000,
            side=OrderSide.BUY,
            quantity=0.01
        )
        
        # Not active without order
        self.assertFalse(level.is_active())
        
        # Active with order
        level.order_id = "12345"
        level.status = "placed"
        self.assertTrue(level.is_active())
        
        # Not active when filled
        level.status = "filled"
        self.assertFalse(level.is_active())


class TestPositionDirection(unittest.TestCase):
    """Test position direction logic"""
    
    def test_long_only_grid(self):
        """Test long-only grid configuration"""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_type=GridType.ARITHMETIC,
            position_direction=PositionDirection.LONG,
            upper_price=45000,
            lower_price=42000,
            grid_count=10,
            total_investment=1000
        )
        
        calculator = GridCalculator(config)
        levels = calculator.calculate_grid_levels(current_price=43500)
        
        # All orders below current price should be buys
        # All orders above should be sells (for profit taking)
        for level in levels:
            if level.price < 43500:
                self.assertEqual(level.side, OrderSide.BUY)
            else:
                self.assertEqual(level.side, OrderSide.SELL)
    
    def test_short_only_grid(self):
        """Test short-only grid configuration"""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_type=GridType.ARITHMETIC,
            position_direction=PositionDirection.SHORT,
            upper_price=45000,
            lower_price=42000,
            grid_count=10,
            total_investment=1000
        )
        
        calculator = GridCalculator(config)
        levels = calculator.calculate_grid_levels(current_price=43500)
        
        # All orders above current price should be sells
        # All orders below should be buys (for profit taking)
        for level in levels:
            if level.price > 43500:
                self.assertEqual(level.side, OrderSide.SELL)
            else:
                self.assertEqual(level.side, OrderSide.BUY)


if __name__ == '__main__':
    unittest.main()