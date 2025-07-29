# Unified Exchange Trading Platform

A modern, high-performance cryptocurrency trading platform inspired by FTX's design, built with FastAPI (backend) and Next.js (frontend). The platform provides a unified interface for trading across multiple exchanges with real-time data streaming.

## Features

### Core Trading Features
- **Real-time Market Data**: Live price updates, order book depth, and trade feed
- **Advanced Trading Interface**: Professional trading UI with TradingView charts
- **Multi-Exchange Support**: Trade on BitUnix and LMEX through a single interface
- **WebSocket Streaming**: Real-time updates for all market data and account information
- **Order Management**: Place, modify, and cancel orders with various order types
- **Position Tracking**: Monitor open positions with real-time P&L calculations

### Technical Features
- **High Performance**: Built with FastAPI for blazing-fast API responses
- **Type Safety**: Full TypeScript support in the frontend
- **Real-time Updates**: WebSocket connections with automatic reconnection
- **Dark Theme**: FTX-inspired dark theme optimized for extended trading sessions
- **Responsive Design**: Works on desktop and tablet devices
- **API Documentation**: Interactive API docs with Swagger UI

## Architecture

```
├── backend/                 # FastAPI backend
│   ├── api/                # API endpoints
│   ├── core/              # Core configuration
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic
│   └── websocket/         # WebSocket handling
│
├── frontend/               # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── lib/               # API client & utilities
│   ├── hooks/             # Custom React hooks
│   └── types/             # TypeScript types
│
└── exchanges/              # Exchange abstraction layer
    ├── base.py            # Abstract interfaces
    ├── bitunix.py         # BitUnix implementation
    └── lmex.py            # LMEX implementation
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Redis (optional, for caching)

### Installation & Running

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd python-exchange-clients
   ```

2. **Start the platform**
   ```bash
   ./start_trading_platform.sh
   ```

   This script will:
   - Create Python virtual environment
   - Install all dependencies
   - Start the FastAPI backend (port 8000)
   - Start the Next.js frontend (port 3000)

3. **Access the platform**
   - Trading Interface: http://localhost:3000
   - API Documentation: http://localhost:8000/api/v1/docs
   - Backend Health: http://localhost:8000/health

### Manual Setup

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Testing

Run the test suite to verify everything is working:

```bash
./test_trading_platform.py
```

This will test:
- API endpoint availability
- WebSocket connections
- Real-time data streaming
- System integration

## API Endpoints

### Market Data
- `GET /api/v1/market/tickers` - Get all tickers
- `GET /api/v1/market/ticker/{symbol}` - Get specific ticker
- `GET /api/v1/market/orderbook/{symbol}` - Get order book
- `GET /api/v1/market/trades/{symbol}` - Get recent trades
- `GET /api/v1/market/candles/{symbol}` - Get candlestick data

### Trading
- `POST /api/v1/trading/order` - Place new order
- `DELETE /api/v1/trading/order/{order_id}` - Cancel order
- `GET /api/v1/trading/orders` - Get open orders
- `GET /api/v1/trading/positions` - Get positions

### Account
- `POST /api/v1/account/login` - User login
- `GET /api/v1/account/balance` - Get account balance
- `POST /api/v1/account/api-keys` - Add exchange API keys

### WebSocket
- `WS /api/v1/ws/connect` - WebSocket connection

## WebSocket Subscriptions

```javascript
// Subscribe to ticker updates
{
  "type": "subscribe",
  "channel": "ticker",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}

// Subscribe to orderbook
{
  "type": "subscribe",
  "channel": "orderbook",
  "symbols": ["BTCUSDT"]
}

// Subscribe to trades
{
  "type": "subscribe",
  "channel": "trades",
  "symbols": ["BTCUSDT"]
}
```

## Configuration

### Backend Configuration
Edit `backend/core/config.py` or create a `.env` file:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
```

### Frontend Configuration
Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws/connect
```

## Exchange API Keys

To trade on real exchanges, add your API keys through the UI or API:

```bash
curl -X POST http://localhost:8000/api/v1/account/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "exchange": "bitunix",
    "api_key": "your-api-key",
    "api_secret": "your-api-secret"
  }'
```

## Development

### Backend Development
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Code Style
- Backend: Follow PEP 8
- Frontend: ESLint + Prettier configuration included

## Production Deployment

### Using Docker (Recommended)
```bash
docker-compose up -d
```

### Manual Deployment
1. Set production environment variables
2. Build frontend: `npm run build`
3. Run backend with production server: `gunicorn main:app`
4. Use nginx as reverse proxy
5. Set up SSL certificates

## Troubleshooting

### Backend Issues
- **Import errors**: Ensure you're in the virtual environment
- **Connection refused**: Check if port 8000 is available
- **Exchange errors**: Verify API keys and network connectivity

### Frontend Issues
- **API connection failed**: Check backend is running
- **WebSocket disconnected**: Check browser console for errors
- **Build errors**: Clear `.next` folder and rebuild

### Common Solutions
1. **Clear caches**: `rm -rf frontend/.next frontend/node_modules`
2. **Reinstall dependencies**: `pip install -r requirements.txt` and `npm install`
3. **Check logs**: Backend logs in terminal, frontend in browser console

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Security Notes

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Enable CORS only for trusted origins
- Implement rate limiting in production
- Use HTTPS in production

## License

This project is licensed under the MIT License.

## Acknowledgments

- Design inspired by FTX exchange (2021-2022)
- Built with FastAPI and Next.js
- TradingView Lightweight Charts for charting
- Exchange abstraction layer for multi-exchange support