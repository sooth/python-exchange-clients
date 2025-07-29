'use client'

import { useState, useCallback } from 'react'
import { useWebSocketSubscription } from '@/hooks/useWebSocket'

interface Trade {
  id: string
  price: number
  amount: number
  side: 'buy' | 'sell'
  timestamp: string
}

interface RecentTradesProps {
  symbol: string
}

export function RecentTrades({ symbol }: RecentTradesProps) {
  const [trades, setTrades] = useState<Trade[]>([])

  // Subscribe to trades updates
  const handleTradeUpdate = useCallback((_, data: Trade[]) => {
    // Keep only the latest 50 trades
    setTrades(prevTrades => {
      const newTrades = [...data, ...prevTrades]
      return newTrades.slice(0, 50)
    })
  }, [])

  useWebSocketSubscription<Trade[]>(
    'trades',
    [symbol],
    handleTradeUpdate
  )

  const formatPrice = (price: number | string) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price
    if (isNaN(numPrice)) return '0.00'
    if (numPrice >= 1000) return numPrice.toFixed(0)
    if (numPrice >= 1) return numPrice.toFixed(2)
    return numPrice.toFixed(4)
  }

  const formatAmount = (amount: number | string) => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
    if (isNaN(numAmount)) return '0.00'
    if (numAmount >= 1000000) return `${(numAmount / 1000000).toFixed(3)}M`
    if (numAmount >= 1000) return `${(numAmount / 1000).toFixed(3)}K`
    return numAmount.toFixed(3)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="h-full flex flex-col bg-[#1a1d29]">
      {/* Header */}
      <div className="px-2 py-1 border-b border-gray-600">
        <h3 className="text-xs font-medium text-gray-400">TRADE HISTORY</h3>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-3 text-xs text-gray-400 px-2 py-1 border-b border-gray-600">
        <div>Price (USD)</div>
        <div className="text-right">Size</div>
        <div className="text-right">Time</div>
      </div>

      {/* Trades list */}
      <div className="flex-1 overflow-y-auto">
        {trades.length === 0 ? (
          <div className="text-center text-gray-400 text-xs p-4">
            No recent trades
          </div>
        ) : (
          trades.map((trade) => (
            <div 
              key={trade.id} 
              className="grid grid-cols-3 text-xs px-2 py-0.5 hover:bg-[#2a2d3a]"
            >
              <div className={`font-mono tabular-nums ${trade.side === 'buy' ? 'text-[#00d395]' : 'text-[#f6465d]'}`}>
                {formatPrice(trade.price)}
              </div>
              <div className="text-right font-mono tabular-nums">
                {formatAmount(trade.amount)}
              </div>
              <div className="text-right text-gray-400">
                {formatTime(trade.timestamp)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}