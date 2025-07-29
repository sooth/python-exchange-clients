'use client'

import { useState, useEffect } from 'react'
import { tradingApi } from '@/lib/api'
import { useWebSocketSubscription } from '@/hooks/useWebSocket'
import { useQuery } from '@tanstack/react-query'
import type { OrderResponse } from '@/types/api'
import toast from 'react-hot-toast'
import { useMarket } from '@/contexts/MarketContext'

interface OpenOrdersProps {
  symbol?: string
  exchange?: string
}

const SHOW_ALL_SYMBOLS_KEY = 'trading-orders-show-all'
const SHOW_REGULAR_ORDERS_KEY = 'trading-orders-show-regular'
const SHOW_TPSL_ORDERS_KEY = 'trading-orders-show-tpsl'

export function OpenOrders({ symbol, exchange }: OpenOrdersProps) {
  const [cancelling, setCancelling] = useState<string[]>([])
  const [showAllSymbols, setShowAllSymbols] = useState(() => {
    // Initialize from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(SHOW_ALL_SYMBOLS_KEY)
      return saved === 'true'
    }
    return false
  })
  const { setSelectedSymbol } = useMarket()
  const [orderTypeFilter, setOrderTypeFilter] = useState<'all' | 'orders' | 'tpsl'>(() => {
    // Initialize from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(SHOW_REGULAR_ORDERS_KEY)
      return saved || 'all'
    }
    return 'all'
  })

  // Fetch orders using react-query
  const { data: fetchedOrders = [], isLoading, error } = useQuery({
    queryKey: ['orders', showAllSymbols ? null : symbol, exchange],
    queryFn: async () => {
      const orders = await tradingApi.getOrders(showAllSymbols ? undefined : symbol, exchange)
      return orders
    },
    refetchInterval: 5000,
  })

  // Log any errors
  if (error) {
    console.error('Error fetching orders:', error)
  }


  // Save preferences to localStorage
  useEffect(() => {
    localStorage.setItem(SHOW_ALL_SYMBOLS_KEY, String(showAllSymbols))
  }, [showAllSymbols])

  useEffect(() => {
    localStorage.setItem(SHOW_REGULAR_ORDERS_KEY, orderTypeFilter)
  }, [orderTypeFilter])

  // Subscribe to order updates
  // Note: Currently disabled since we're using polling via react-query
  // When WebSocket order updates are implemented, we can invalidate the query here

  const handleCancel = async (orderId: string, orderSymbol: string) => {
    setCancelling(prev => [...prev, orderId])
    
    try {
      await tradingApi.cancelOrder(orderId, orderSymbol, exchange)
      toast.success('Order cancelled')
      // Order list will be refreshed by react-query
    } catch (error) {
      console.error('Failed to cancel order:', error)
      toast.error('Failed to cancel order')
    } finally {
      setCancelling(prev => prev.filter(id => id !== orderId))
    }
  }

  const formatPrice = (price?: number | string) => {
    if (!price) return '-'
    const numPrice = typeof price === 'string' ? parseFloat(price) : price
    if (isNaN(numPrice)) return '0.00'
    if (numPrice >= 1000) return numPrice.toFixed(0)
    if (numPrice >= 1) return numPrice.toFixed(2)
    return numPrice.toFixed(4)
  }

  const formatAmount = (amount: number | string) => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
    if (isNaN(numAmount)) return '0.00'
    if (numAmount >= 1000) return numAmount.toFixed(0)
    if (numAmount >= 1) return numAmount.toFixed(2)
    return numAmount.toFixed(4)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Debug: Log order types to understand the issue
  useEffect(() => {
    if (fetchedOrders.length > 0) {
      console.log('Order types debug:', fetchedOrders.map(o => ({
        symbol: o.symbol,
        side: o.side,
        type: o.type,
        price: o.price,
        stopPrice: (o as any).stopPrice,
        triggerPrice: (o as any).triggerPrice,
        reduceOnly: (o as any).reduceOnly,
        allFields: Object.keys(o)
      })))
    }
  }, [fetchedOrders])

  // Filter orders based on type
  const filteredOrders = fetchedOrders.filter(order => {
    if (orderTypeFilter === 'all') return true
    
    // Use the new fields from backend
    const hasStopPrice = order.stop_price && order.stop_price !== order.price
    const hasTriggerPrice = order.trigger_price
    const isReduceOnly = order.reduce_only
    
    // Check order type
    const lowerType = order.type.toLowerCase()
    const rawType = order.raw_type?.toLowerCase() || ''
    
    const isExplicitTPSL = lowerType === 'stop' || 
                          lowerType === 'stop_limit' || 
                          lowerType === 'take_profit' || 
                          lowerType === 'take_profit_limit' ||
                          lowerType === 'stop_market' ||
                          lowerType === 'take_profit_market' ||
                          lowerType.includes('stop') ||
                          lowerType.includes('tp') ||
                          lowerType.includes('sl') ||
                          rawType.includes('stop') ||
                          rawType.includes('tp') ||
                          rawType.includes('sl')
    
    // Check if it's a TP/SL based on multiple criteria
    const isTPSLOrder = isExplicitTPSL || hasStopPrice || hasTriggerPrice
    
    // For debugging - log AVAX-PERP orders
    if (order.symbol === 'AVAX-PERP') {
      console.log('AVAX-PERP order debug:', {
        type: order.type,
        raw_type: order.raw_type,
        isTPSL: isTPSLOrder,
        stop_price: order.stop_price,
        trigger_price: order.trigger_price,
        reduce_only: order.reduce_only,
        price: order.price,
        allFields: order
      })
    }
    
    if (orderTypeFilter === 'orders' && isTPSLOrder) return false
    if (orderTypeFilter === 'tpsl' && !isTPSLOrder) return false
    
    return true
  })

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-400 text-xs">Loading orders...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex flex-col">
        <div className="flex items-center justify-between border-b border-gray-600">
          <div className="flex">
            <button
              className={`px-4 py-2 text-xs font-medium ${
                orderTypeFilter === 'all'
                  ? 'text-white border-b-2 border-[#00d395]'
                  : 'text-gray-400 hover:text-white'
              }`}
              onClick={() => setOrderTypeFilter('all')}
            >
              All Orders
            </button>
            <button
              className={`px-4 py-2 text-xs font-medium ${
                orderTypeFilter === 'orders'
                  ? 'text-white border-b-2 border-[#00d395]'
                  : 'text-gray-400 hover:text-white'
              }`}
              onClick={() => setOrderTypeFilter('orders')}
            >
              Orders
            </button>
            <button
              className={`px-4 py-2 text-xs font-medium ${
                orderTypeFilter === 'tpsl'
                  ? 'text-white border-b-2 border-[#00d395]'
                  : 'text-gray-400 hover:text-white'
              }`}
              onClick={() => setOrderTypeFilter('tpsl')}
            >
              TP/SL
            </button>
          </div>
          <div className="flex items-center gap-4 px-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="show-all-symbols"
                checked={showAllSymbols}
                onChange={(e) => setShowAllSymbols(e.target.checked)}
                className="w-3 h-3 rounded border-gray-600 bg-[#1a1d29] text-[#00d395] focus:ring-1 focus:ring-[#00d395]"
              />
              <label htmlFor="show-all-symbols" className="text-xs text-gray-400 cursor-pointer">
                Show all symbols
              </label>
            </div>
            <div className="text-xs text-gray-400">
              {filteredOrders.length} {filteredOrders.length === 1 ? 'order' : 'orders'}
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-x-auto overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-[#2a2d3a]">
        <table className="w-full min-w-[700px]">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left px-3 py-2 text-xs text-gray-400 font-normal">Symbol</th>
              <th className="text-left px-3 py-2 text-xs text-gray-400 font-normal">Type</th>
              <th className="text-left px-3 py-2 text-xs text-gray-400 font-normal">Side</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">Price</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">Size</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">Filled</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">Time</th>
              <th className="text-center px-3 py-2 text-xs text-gray-400 font-normal">Actions</th>
            </tr>
          </thead>
        <tbody>
          {filteredOrders.length === 0 ? (
            <tr>
              <td colSpan={8} className="text-center py-8 text-gray-400 text-xs">
                No open orders
              </td>
            </tr>
          ) : (
            filteredOrders.map((order) => (
              <tr 
                key={order.id} 
                className="border-b border-gray-700 hover:bg-[#2a2d3a]"
              >
                <td className="px-3 py-2 text-xs font-medium">
                  <button
                    onClick={() => setSelectedSymbol(order.symbol)}
                    className="hover:text-[#00d395] hover:underline transition-colors cursor-pointer"
                    title="Click to view market"
                  >
                    {order.symbol}
                  </button>
                </td>
                <td className="px-3 py-2 text-xs">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    (() => {
                      // Match the filter logic
                      const hasStopPrice = order.stop_price && order.stop_price !== order.price
                      const hasTriggerPrice = order.trigger_price
                      const lowerType = order.type.toLowerCase()
                      const rawType = order.raw_type?.toLowerCase() || ''
                      
                      const isTPSLOrder = lowerType === 'stop' || 
                                          lowerType === 'stop_limit' || 
                                          lowerType === 'take_profit' || 
                                          lowerType === 'take_profit_limit' ||
                                          lowerType === 'stop_market' ||
                                          lowerType === 'take_profit_market' ||
                                          lowerType.includes('stop') ||
                                          lowerType.includes('tp') ||
                                          lowerType.includes('sl') ||
                                          rawType.includes('stop') ||
                                          rawType.includes('tp') ||
                                          rawType.includes('sl') ||
                                          hasStopPrice || 
                                          hasTriggerPrice
                      
                      return isTPSLOrder 
                        ? 'bg-yellow-500/10 text-yellow-500' 
                        : 'bg-[#2a2d3a] text-gray-400'
                    })()
                  }`}>
                    {order.type.toUpperCase()}
                  </span>
                </td>
                <td className={`px-3 py-2 text-xs font-medium ${
                  order.side === 'buy' ? 'text-[#00d395]' : 'text-[#f6465d]'
                }`}>
                  {order.side.toUpperCase()}
                </td>
                <td className="text-right px-3 py-2 text-xs font-mono tabular-nums">
                  {formatPrice(order.price)}
                </td>
                <td className="text-right px-3 py-2 text-xs font-mono tabular-nums">
                  {formatAmount(order.amount)}
                </td>
                <td className="text-right px-3 py-2 text-xs">
                  <div className="flex items-center justify-end space-x-1">
                    <span className="font-mono tabular-nums">
                      {formatAmount(order.filled)}
                    </span>
                    <span className="text-gray-400">
                      ({((order.filled / order.amount) * 100).toFixed(1)}%)
                    </span>
                  </div>
                </td>
                <td className="text-right px-3 py-2 text-xs text-gray-400">
                  {formatTime(order.timestamp)}
                </td>
                <td className="text-center px-3 py-2">
                  <button
                    onClick={() => handleCancel(order.id, order.symbol)}
                    disabled={cancelling.includes(order.id)}
                    className="text-xs text-[#00d395] hover:text-[#00c584] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {cancelling.includes(order.id) ? 'Cancelling...' : 'Cancel'}
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
        </table>
      </div>
    </div>
  )
}