'use client'

import { useQuery } from '@tanstack/react-query'
import { marketApi } from '@/lib/api'
import { useWebSocketSubscription } from '@/hooks/useWebSocket'
import { useState, useEffect } from 'react'
import type { Ticker, SymbolInfo } from '@/types/api'
import { getOrderbookWebSocket, type BestBidAsk } from '@/lib/websocket/lmexOrderbookWebSocket'
import { useMarket } from '@/contexts/MarketContext'

interface MarketInfoProps {
  symbol: string
  exchange?: string
}

export function MarketInfo({ symbol, exchange }: MarketInfoProps) {
  const [tickerData, setTickerData] = useState<Ticker | null>(null)
  const [bidAsk, setBidAsk] = useState<BestBidAsk | null>(null)
  const { selectedExchange } = useMarket()

  // Fetch symbol info
  const { data: symbolInfo } = useQuery({
    queryKey: ['symbol', symbol, exchange],
    queryFn: () => marketApi.getSymbolInfo(symbol, exchange),
    enabled: !!symbol,
  })

  // Fetch initial ticker data
  const { data: ticker } = useQuery({
    queryKey: ['ticker', symbol, exchange],
    queryFn: () => marketApi.getTicker(symbol, exchange),
    enabled: !!symbol,
    refetchInterval: 5000,
  })

  // Subscribe to real-time ticker updates
  useWebSocketSubscription<Ticker>(
    'ticker',
    symbol ? [symbol] : [],
    (sym, data) => {
      if (sym === symbol) {
        setTickerData(data)
      }
    }
  )

  const currentTicker = tickerData || ticker

  // Subscribe to orderbook WebSocket for bid/ask prices
  useEffect(() => {
    if (selectedExchange !== 'lmex' || !symbol) return

    const ws = getOrderbookWebSocket(true) // true for futures
    
    // Connect and subscribe
    ws.connect(
      (newBidAsk) => {
        if (newBidAsk.symbol === symbol) {
          setBidAsk(newBidAsk)
        }
      },
      (error) => {
        console.error('Orderbook WebSocket error:', error)
      }
    )

    ws.subscribeToBestBidAsk(symbol)

    return () => {
      ws.unsubscribeFromBestBidAsk(symbol)
    }
  }, [symbol, selectedExchange])

  const formatPrice = (price: number | string | undefined) => {
    if (!price) return '0.00'
    const numPrice = typeof price === 'string' ? parseFloat(price) : price
    if (isNaN(numPrice)) return '0.00'
    if (numPrice >= 1000) return numPrice.toFixed(0)
    if (numPrice >= 1) return numPrice.toFixed(2)
    if (numPrice >= 0.01) return numPrice.toFixed(4)
    return numPrice.toFixed(6)
  }

  const formatVolume = (volume: number | string | undefined) => {
    if (!volume) return '0'
    const numVolume = typeof volume === 'string' ? parseFloat(volume) : volume
    if (isNaN(numVolume)) return '0'
    if (numVolume >= 1e9) return `${(numVolume / 1e9).toFixed(2)}B`
    if (numVolume >= 1e6) return `${(numVolume / 1e6).toFixed(2)}M`
    if (numVolume >= 1e3) return `${(numVolume / 1e3).toFixed(2)}K`
    return numVolume.toFixed(0)
  }

  if (!currentTicker) {
    return (
      <div className="h-full flex items-center px-4">
        <div className="text-sm text-gray-400">Loading market data...</div>
      </div>
    )
  }

  const changePercent = parseFloat(currentTicker.change_percent as any) || 0
  const isPositive = changePercent >= 0

  return (
    <div className="h-full flex items-center px-4 space-x-8">
      {/* Symbol name */}
      <div className="flex items-center space-x-3">
        <h2 className="text-lg font-semibold">{symbol}</h2>
        <span className="text-xs text-gray-400">Perpetual</span>
      </div>

      {/* Price */}
      <div className="flex items-center space-x-2">
        <span className={`text-2xl font-semibold tabular-nums ${isPositive ? 'text-[#00d395]' : 'text-[#f6465d]'}`}>
          ${formatPrice(currentTicker.last)}
        </span>
        <div className="flex flex-col">
          <span className={`text-xs font-medium ${isPositive ? 'text-[#00d395]' : 'text-[#f6465d]'}`}>
            {isPositive ? '+' : ''}{isNaN(changePercent) ? '0.00' : changePercent.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center space-x-6 text-xs">
        <div className="flex flex-col">
          <span className="text-gray-400">Bid</span>
          <span className="font-medium tabular-nums text-[#00d395]">
            ${formatPrice(bidAsk?.bid || currentTicker.bid)}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-400">Ask</span>
          <span className="font-medium tabular-nums text-[#f6465d]">
            ${formatPrice(bidAsk?.ask || currentTicker.ask)}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-400">24h High</span>
          <span className="font-medium tabular-nums">${formatPrice(currentTicker.high)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-400">24h Low</span>
          <span className="font-medium tabular-nums">${formatPrice(currentTicker.low)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-400">24h Volume</span>
          <span className="font-medium tabular-nums">${formatVolume(currentTicker.quote_volume)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-400">Funding</span>
          <span className="font-medium tabular-nums text-[#00d395]">0.0100%</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-400">Open Interest</span>
          <span className="font-medium tabular-nums">${formatVolume(currentTicker.volume)}</span>
        </div>
      </div>

      {/* Right side - Additional info */}
      <div className="ml-auto flex items-center space-x-4 text-xs">
        <button className="text-gray-400 hover:text-white">
          Index: ${formatPrice(currentTicker.last)}
        </button>
        <button className="text-gray-400 hover:text-white">
          USD Value
        </button>
      </div>
    </div>
  )
}