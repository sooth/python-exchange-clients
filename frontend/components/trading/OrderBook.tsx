'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { useWebSocketSubscription } from '@/hooks/useWebSocket'
import type { OrderBook as OrderBookType, OrderBookLevel } from '@/types/api'

interface OrderBookProps {
  symbol: string
}

interface ExtendedOrderBookLevel extends OrderBookLevel {
  total: number
}

export function OrderBook({ symbol }: OrderBookProps) {
  const [orderBook, setOrderBook] = useState<OrderBookType | null>(null)
  const [grouping, setGrouping] = useState(0.1)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isSmallContainer, setIsSmallContainer] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Subscribe to orderbook updates
  useWebSocketSubscription<OrderBookType>(
    'orderbook',
    [symbol],
    (_, data) => {
      setOrderBook(data)
    }
  )

  // Detect container size
  useEffect(() => {
    if (!containerRef.current) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = entry.contentRect.width
        setIsSmallContainer(width < 300)
      }
    })

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  // Calculate depth percentages
  const { bids, asks, maxTotal } = useMemo(() => {
    if (!orderBook) return { bids: [], asks: [], maxTotal: 0 }

    let bidTotal = 0
    const bidsWithTotal = orderBook.bids.slice(0, 15).map(bid => {
      bidTotal += bid.amount
      return { ...bid, total: bidTotal }
    })

    let askTotal = 0
    const asksWithTotal = orderBook.asks.slice(0, 15).reverse().map(ask => {
      askTotal += ask.amount
      return { ...ask, total: askTotal }
    }).reverse()

    const maxTotal = Math.max(bidTotal, askTotal)

    return { bids: bidsWithTotal, asks: asksWithTotal, maxTotal }
  }, [orderBook])

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

  return (
    <div ref={containerRef} className="h-full flex flex-col bg-[#1a1d29]">
      {/* Header */}
      <div className="px-2 py-1 border-b border-gray-600 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-medium text-gray-400">ORDER BOOK</h3>
          {isSmallContainer && (
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="text-xs text-gray-400 hover:text-white transition-colors"
            >
              [{isCollapsed ? '+' : '-'}]
            </button>
          )}
        </div>
        {!isCollapsed && (
          <select
            value={grouping}
            onChange={(e) => setGrouping(Number(e.target.value))}
            className="bg-[#2a2d3a] border border-gray-600 px-1 py-0.5 text-xs text-gray-400 focus:outline-none"
          >
            <option value={0.01}>0.01</option>
            <option value={0.1}>0.1</option>
            <option value={1}>1</option>
            <option value={10}>10</option>
          </select>
        )}
      </div>

      {isCollapsed ? (
        /* Collapsed summary view */
        <div className="flex-1 flex flex-col justify-center items-center p-4">
          {orderBook && asks.length > 0 && bids.length > 0 ? (
            <div className="text-center">
              <div className="text-sm text-[#00d395] font-mono tabular-nums">
                {formatPrice(bids[0].price)}
              </div>
              <div className="text-xs text-gray-400 my-1">Spread</div>
              <div className="text-sm text-[#f6465d] font-mono tabular-nums">
                {formatPrice(asks[asks.length - 1].price)}
              </div>
            </div>
          ) : (
            <div className="text-xs text-gray-400">No data</div>
          )}
        </div>
      ) : (
        <>
          {/* Column headers */}
          <div className="grid grid-cols-3 text-xs text-gray-400 px-2 py-1 border-b border-gray-600">
            <div>Price (USD)</div>
            <div className="text-right">Size</div>
            <div className="text-right">Total</div>
          </div>

          {/* Order book content */}
          <div className="flex-1 flex flex-col overflow-hidden">
        {/* Asks */}
        <div className="flex-1 overflow-y-auto flex flex-col-reverse">
          {asks.map((ask, i) => (
            <div key={i} className="relative group">
              <div
                className="absolute inset-0 bg-[#f6465d]"
                style={{ 
                  width: `${(ask.total / maxTotal) * 100}%`,
                  opacity: 0.15
                }}
              />
              <div className="relative grid grid-cols-3 text-xs px-2 py-0.5 hover:bg-[#2a2d3a] cursor-pointer">
                <div className="text-[#f6465d] font-mono tabular-nums">{formatPrice(ask.price)}</div>
                <div className="text-right font-mono tabular-nums">{formatAmount(ask.amount)}</div>
                <div className="text-right font-mono tabular-nums text-gray-400">
                  {formatAmount(ask.total)}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Spread */}
        <div className="border-y border-gray-600 px-2 py-1.5 bg-[#2a2d3a]">
          <div className="flex items-center justify-between text-xs">
            {orderBook && asks.length > 0 && bids.length > 0 && (
              <>
                <span className="font-mono tabular-nums text-white">
                  {formatPrice((asks[asks.length - 1].price + bids[0].price) / 2)}
                </span>
                <span className="text-gray-400">
                  Spread: {formatPrice(asks[asks.length - 1].price - bids[0].price)}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Bids */}
        <div className="flex-1 overflow-y-auto">
          {bids.map((bid, i) => (
            <div key={i} className="relative group">
              <div
                className="absolute inset-0 bg-[#00d395]"
                style={{ 
                  width: `${(bid.total / maxTotal) * 100}%`,
                  opacity: 0.15
                }}
              />
              <div className="relative grid grid-cols-3 text-xs px-2 py-0.5 hover:bg-[#2a2d3a] cursor-pointer">
                <div className="text-[#00d395] font-mono tabular-nums">{formatPrice(bid.price)}</div>
                <div className="text-right font-mono tabular-nums">{formatAmount(bid.amount)}</div>
                <div className="text-right font-mono tabular-nums text-gray-400">
                  {formatAmount(bid.total)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
        </>
      )}
    </div>
  )
}