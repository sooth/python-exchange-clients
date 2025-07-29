"""Grid Bot Configuration Management"""

import json
import yaml
import os
from typing import Dict, Any, Optional
from dataclasses import asdict

from .types import GridConfig, GridType, PositionDirection


class GridBotConfig:
    """Manages grid bot configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Optional[GridConfig] = None
        
    def load_from_file(self, path: str) -> GridConfig:
        """Load configuration from JSON or YAML file"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r') as f:
            if path.endswith('.json'):
                data = json.load(f)
            elif path.endswith(('.yml', '.yaml')):
                data = yaml.safe_load(f)
            else:
                raise ValueError("Configuration file must be JSON or YAML")
        
        return self.from_dict(data)
    
    def from_dict(self, data: Dict[str, Any]) -> GridConfig:
        """Create GridConfig from dictionary"""
        # Convert string enums to proper types
        if 'grid_type' in data:
            if isinstance(data['grid_type'], str):
                data['grid_type'] = GridType(data['grid_type'].lower())
        
        if 'position_direction' in data:
            if isinstance(data['position_direction'], str):
                data['position_direction'] = PositionDirection(data['position_direction'].upper())
        
        # Create config object
        config = GridConfig(**data)
        
        # Validate
        errors = config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        self.config = config
        return config
    
    def save_to_file(self, config: GridConfig, path: str):
        """Save configuration to file"""
        data = self.to_dict(config)
        
        with open(path, 'w') as f:
            if path.endswith('.json'):
                json.dump(data, f, indent=2)
            elif path.endswith(('.yml', '.yaml')):
                yaml.dump(data, f, default_flow_style=False)
            else:
                raise ValueError("Configuration file must be JSON or YAML")
    
    def to_dict(self, config: GridConfig) -> Dict[str, Any]:
        """Convert GridConfig to dictionary"""
        data = asdict(config)
        
        # Convert enums to strings
        data['grid_type'] = config.grid_type.value
        data['position_direction'] = config.position_direction.value
        
        return data
    
    def create_default_config(self, symbol: str) -> GridConfig:
        """Create a default configuration for a symbol"""
        return GridConfig(
            symbol=symbol,
            grid_type=GridType.ARITHMETIC,
            position_direction=PositionDirection.NEUTRAL,
            upper_price=0,  # Must be set
            lower_price=0,  # Must be set
            grid_count=20,
            total_investment=1000,
            leverage=1,
            position_mode="one-way",
            margin_mode="cross",
            stop_loss=None,
            take_profit=None,
            max_position_size=None,
            max_drawdown_percentage=20,
            order_type="LIMIT",
            time_in_force="GTC",
            post_only=True,
            auto_restart=True,
            trailing_up=False,
            trailing_down=False,
            cancel_orders_on_stop=True,
            close_position_on_stop=False,
            min_profit_per_grid=None,
            rebalance_threshold=None
        )
    
    def create_from_wizard(self) -> GridConfig:
        """Interactive configuration wizard"""
        print("\n=== Grid Bot Configuration Wizard ===\n")
        
        # Symbol
        symbol = input("Enter trading symbol (e.g., BTCUSDT): ").strip().upper()
        
        # Grid type
        print("\nGrid Type:")
        print("1. Arithmetic (equal price intervals)")
        print("2. Geometric (percentage-based intervals)")
        grid_type_choice = input("Select grid type (1 or 2): ").strip()
        grid_type = GridType.ARITHMETIC if grid_type_choice == "1" else GridType.GEOMETRIC
        
        # Position direction
        print("\nPosition Direction:")
        print("1. Long only")
        print("2. Short only")
        print("3. Neutral (both directions)")
        direction_choice = input("Select position direction (1, 2, or 3): ").strip()
        direction_map = {
            "1": PositionDirection.LONG,
            "2": PositionDirection.SHORT,
            "3": PositionDirection.NEUTRAL
        }
        position_direction = direction_map.get(direction_choice, PositionDirection.NEUTRAL)
        
        # Price range
        print("\nPrice Range:")
        lower_price = float(input("Enter lower price: $"))
        upper_price = float(input("Enter upper price: $"))
        
        # Grid settings
        grid_count = int(input("\nNumber of grid levels (e.g., 20): ") or "20")
        total_investment = float(input("Total investment amount: $"))
        
        # Leverage
        leverage = int(input("\nLeverage (1-125, default 1): ") or "1")
        
        # Risk management
        print("\nRisk Management (press Enter to skip):")
        stop_loss_input = input("Stop loss price: $")
        stop_loss = float(stop_loss_input) if stop_loss_input else None
        
        take_profit_input = input("Take profit percentage (e.g., 50): ")
        take_profit = float(take_profit_input) if take_profit_input else None
        
        # Create config
        config = GridConfig(
            symbol=symbol,
            grid_type=grid_type,
            position_direction=position_direction,
            upper_price=upper_price,
            lower_price=lower_price,
            grid_count=grid_count,
            total_investment=total_investment,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            max_drawdown_percentage=20,
            post_only=True
        )
        
        # Validate
        errors = config.validate()
        if errors:
            print(f"\nConfiguration errors: {', '.join(errors)}")
            return self.create_from_wizard()  # Retry
        
        # Display summary
        print("\n=== Configuration Summary ===")
        print(f"Symbol: {config.symbol}")
        print(f"Grid Type: {config.grid_type.value}")
        print(f"Position Direction: {config.position_direction.value}")
        print(f"Price Range: ${config.lower_price} - ${config.upper_price}")
        print(f"Grid Count: {config.grid_count}")
        print(f"Grid Spacing: ${config.grid_spacing:.2f}")
        print(f"Total Investment: ${config.total_investment}")
        print(f"Investment per Grid: ${config.investment_per_grid:.2f}")
        print(f"Leverage: {config.leverage}x")
        
        if config.stop_loss:
            print(f"Stop Loss: ${config.stop_loss}")
        if config.take_profit:
            print(f"Take Profit: {config.take_profit}%")
        
        confirm = input("\nConfirm configuration? (y/n): ").strip().lower()
        if confirm != 'y':
            return self.create_from_wizard()  # Retry
        
        self.config = config
        return config
    
    def get_example_configs(self) -> Dict[str, GridConfig]:
        """Get example configurations for different strategies"""
        return {
            'conservative': GridConfig(
                symbol="BTCUSDT",
                grid_type=GridType.ARITHMETIC,
                position_direction=PositionDirection.NEUTRAL,
                upper_price=45000,
                lower_price=40000,
                grid_count=20,
                total_investment=1000,
                leverage=1,
                stop_loss=38000,
                max_drawdown_percentage=10
            ),
            'aggressive': GridConfig(
                symbol="BTCUSDT",
                grid_type=GridType.GEOMETRIC,
                position_direction=PositionDirection.LONG,
                upper_price=45000,
                lower_price=42000,
                grid_count=50,
                total_investment=5000,
                leverage=10,
                take_profit=50,
                trailing_up=True
            ),
            'scalping': GridConfig(
                symbol="ETHUSDT",
                grid_type=GridType.ARITHMETIC,
                position_direction=PositionDirection.NEUTRAL,
                upper_price=2600,
                lower_price=2500,
                grid_count=100,
                total_investment=10000,
                leverage=5,
                min_profit_per_grid=0.1
            )
        }