#!/bin/bash

echo "Clearing all caches and restarting..."

# Kill any running processes
echo "Stopping all services..."
pkill -f "uvicorn backend.main:app" || true
pkill -f "next dev" || true
sleep 2

# Clear Next.js cache
echo "Clearing Next.js cache..."
rm -rf frontend/.next
rm -rf frontend/node_modules/.cache

# Clear browser localStorage hint
echo ""
echo "⚠️  IMPORTANT: Clear your browser cache and localStorage!"
echo "   1. Open Chrome DevTools (F12)"
echo "   2. Go to Application tab"
echo "   3. Click 'Clear storage' under Storage"
echo "   4. Click 'Clear site data'"
echo ""
echo "Press Enter when done..."
read

# Start the platform
echo "Starting platform with LMEX only..."
./start_trading_platform.sh