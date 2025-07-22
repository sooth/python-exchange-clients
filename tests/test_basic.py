"""Basic tests for the exchange library"""

import pytest
from unittest.mock import Mock, patch
from exchanges.lmex import LMEXExchange
from exchanges.bitunix import BitUnixExchange
from exchanges.base import ExchangeOrderRequest, ExchangeTicker


class TestLMEXExchange:
    """Test LMEX exchange functionality"""
    
    def test_initialization(self):
        """Test LMEX exchange initialization"""
        exchange = LMEXExchange()
        assert exchange.base_url == "https://api.lmex.io/futures"
        assert exchange.precision_manager is not None
    
    @patch('requests.get')
    def test_fetch_tickers(self, mock_get):
        """Test fetching tickers"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "symbol": "BTC-PERP",
                "last": "65000",
                "bid": "64999",
                "ask": "65001",
                "volume": "1000000",
                "contractSize": 0.00001
            }
        ]
        mock_get.return_value = mock_response
        
        exchange = LMEXExchange()
        
        # Test callback
        result_status = None
        result_data = None
        
        def callback(status, data):
            nonlocal result_status, result_data
            result_status = status
            result_data = data
        
        exchange.fetchTickers(callback)
        
        assert result_status == "success"
        assert len(result_data) == 1
        assert result_data[0].symbol == "BTC-PERP"
        assert result_data[0].lastPrice == 65000.0
    
    @patch('requests.post')
    def test_place_order(self, mock_post):
        """Test placing an order"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"orderID": "12345", "symbol": "BTC-PERP", "status": "NEW"}'
        mock_post.return_value = mock_response
        
        exchange = LMEXExchange()
        
        # Mock precision manager methods
        exchange.precision_manager.get_price_precision = Mock(return_value=2)
        exchange.precision_manager.get_quantity_precision = Mock(return_value=4)
        exchange.precision_manager.get_min_quantity = Mock(return_value=1)
        exchange.precision_manager.get_contract_size = Mock(return_value=0.00001)
        
        # Create order request
        order = ExchangeOrderRequest(
            symbol="BTC-PERP",
            side="LONG",
            orderType="LIMIT",
            qty=0.001,
            price=65000.0,
            timeInForce="GTC"
        )
        
        # Test callback
        result_status = None
        result_data = None
        
        def callback(status, data):
            nonlocal result_status, result_data
            result_status = status
            result_data = data
        
        exchange.placeOrder(order, callback)
        
        assert result_status == "success"
        assert result_data.orderId == "12345"


class TestBitUnixExchange:
    """Test BitUnix exchange functionality"""
    
    def test_initialization(self):
        """Test BitUnix exchange initialization"""
        exchange = BitUnixExchange()
        assert exchange.base_url == "https://api.bitunix.com"
        assert exchange.precision_manager is not None
    
    @patch('requests.get')
    def test_fetch_tickers(self, mock_get):
        """Test fetching tickers"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "00000",
            "data": [
                {
                    "symbol": "BTCUSDT",
                    "lastPr": "65000",
                    "askPr": "65001",
                    "bidPr": "64999",
                    "high24h": "66000",
                    "low24h": "64000",
                    "volume24h": "1000000"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        exchange = BitUnixExchange()
        
        # Test callback
        result_status = None
        result_data = None
        
        def callback(status, data):
            nonlocal result_status, result_data
            result_status = status
            result_data = data
        
        exchange.fetchTickers(callback)
        
        assert result_status == "success"
        assert len(result_data) == 1
        assert result_data[0].symbol == "BTCUSDT"
        assert result_data[0].lastPrice == 65000.0


class TestExchangeOrderRequest:
    """Test ExchangeOrderRequest data class"""
    
    def test_order_request_creation(self):
        """Test creating an order request"""
        order = ExchangeOrderRequest(
            symbol="BTC-PERP",
            side="LONG",
            orderType="LIMIT",
            qty=0.001,
            price=65000.0,
            timeInForce="GTC"
        )
        
        assert order.symbol == "BTC-PERP"
        assert order.side == "LONG"
        assert order.orderType == "LIMIT"
        assert order.qty == 0.001
        assert order.price == 65000.0
        assert order.timeInForce == "GTC"
        assert order.orderLinkId is None


if __name__ == "__main__":
    pytest.main([__file__])