'use client'

import { useState, useEffect, useMemo } from 'react'
import { tradingApi, accountApi } from '@/lib/api'
import { useWebSocketSubscription } from '@/hooks/useWebSocket'
import { useQuery } from '@tanstack/react-query'
import type { Position } from '@/types/api'
import toast from 'react-hot-toast'
import { useMarket } from '@/contexts/MarketContext'

interface PositionsProps {
  exchange?: string
}

export function Positions({ exchange }: PositionsProps) {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [sortColumn, setSortColumn] = useState<'pnl' | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const { setSelectedSymbol } = useMarket()

  // Fetch account balance
  const { data: accountInfo, error: balanceError } = useQuery({
    queryKey: ['balance', exchange],
    queryFn: async () => {
      console.log('Fetching balance...', { exchange })
      const balance = await accountApi.getBalance(exchange)
      console.log('Fetched balance:', balance)
      return balance
    },
    refetchInterval: 10000,
  })

  // Log balance errors
  if (balanceError) {
    console.error('Error fetching balance:', balanceError)
  }

  // Fetch positions with periodic refresh
  useEffect(() => {
    const fetchPositions = async () => {
      try {
        console.log('Fetching positions...', { exchange })
        const data = await tradingApi.getPositions(exchange)
        console.log('Fetched positions:', data)
        setPositions(data)
      } catch (error) {
        console.error('Failed to fetch positions:', error)
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchPositions()

    // Set up periodic refresh every 5 seconds (more frequent than balance)
    const interval = setInterval(fetchPositions, 5000)

    return () => clearInterval(interval)
  }, [exchange])

  // Subscribe to position updates (for exchanges that support position streaming)
  // Note: LMEX doesn't support position streaming, so we rely on polling above
  useWebSocketSubscription<Position[]>(
    'positions',
    ['*'],
    (_, data) => {
      console.log('WebSocket positions update:', data)
      setPositions(data)
    }
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
    if (Math.abs(numAmount) >= 1000) return numAmount.toFixed(0)
    if (Math.abs(numAmount) >= 1) return numAmount.toFixed(2)
    return numAmount.toFixed(4)
  }

  const formatPnL = (pnl: number | string) => {
    const numPnl = typeof pnl === 'string' ? parseFloat(pnl) : pnl
    if (isNaN(numPnl)) return '0.00'
    const formatted = Math.abs(numPnl) >= 1000 
      ? numPnl.toFixed(0) 
      : Math.abs(numPnl) >= 1 
        ? numPnl.toFixed(2) 
        : numPnl.toFixed(4)
    
    return numPnl >= 0 ? `+${formatted}` : formatted
  }

  const formatPercentage = (percentage: number | string) => {
    const numPercentage = typeof percentage === 'string' ? parseFloat(percentage) : percentage
    if (isNaN(numPercentage)) return '0.00%'
    const formatted = numPercentage.toFixed(2)
    return numPercentage >= 0 ? `+${formatted}%` : `${formatted}%`
  }

  const formatCurrency = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(numValue)) return '0.00'
    return numValue.toFixed(2)
  }

  // Handle PnL column click
  const handlePnLSort = () => {
    if (sortColumn === 'pnl') {
      if (sortDirection === 'desc') {
        setSortDirection('asc')
      } else {
        // Reset to unsorted
        setSortColumn(null)
      }
    } else {
      // Start with descending (highest PnL first)
      setSortColumn('pnl')
      setSortDirection('desc')
    }
  }

  // Sort positions based on PnL
  const sortedPositions = useMemo(() => {
    if (!sortColumn) return positions

    return [...positions].sort((a, b) => {
      const aValue = a.unrealized_pnl || 0
      const bValue = b.unrealized_pnl || 0

      if (sortDirection === 'asc') {
        return aValue - bValue
      } else {
        return bValue - aValue
      }
    })
  }, [positions, sortColumn, sortDirection])

  return (
    <div className="h-full flex flex-col">
      {/* Balances table */}
      <div className="overflow-x-auto overflow-y-hidden scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-[#2a2d3a]">
        <table className="w-full min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left px-3 py-2 text-xs text-gray-400 font-normal">Coin</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">Balance</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">Available</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal">USD Value</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal whitespace-nowrap">Base Currency</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal whitespace-nowrap">Quote Currency</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal whitespace-nowrap">Change Ratio</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal whitespace-nowrap">24h Volume</th>
              <th className="text-right px-3 py-2 text-xs text-gray-400 font-normal"></th>
            </tr>
          </thead>
          <tbody>
            {accountInfo?.balances && Object.entries(accountInfo.balances).length > 0 ? (
              Object.entries(accountInfo.balances).map(([coin, balance]) => (
              <tr key={coin} className="border-b border-gray-700 hover:bg-[#2a2d3a]">
                <td className="px-3 py-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-5 h-5 rounded-full bg-[#2a2d3a] flex items-center justify-center text-xs font-medium">
                      {coin.charAt(0)}
                    </div>
                    <span className="text-sm font-medium">{coin}</span>
                  </div>
                </td>
                <td className="text-right px-3 py-2 text-sm font-mono tabular-nums">
                  {formatCurrency(balance.total)}
                </td>
                <td className="text-right px-3 py-2 text-sm font-mono tabular-nums">
                  {formatCurrency(balance.free)}
                </td>
                <td className="text-right px-3 py-2 text-sm font-mono tabular-nums">
                  ${formatCurrency(balance.total)}
                </td>
                <td className="text-right px-3 py-2 text-sm text-gray-400">
                  -
                </td>
                <td className="text-right px-3 py-2 text-sm text-gray-400">
                  -
                </td>
                <td className="text-right px-3 py-2 text-sm text-gray-400">
                  -
                </td>
                <td className="text-right px-3 py-2 text-sm text-gray-400">
                  -
                </td>
                <td className="text-right px-3 py-2">
                  <div className="flex items-center justify-end space-x-2">
                    <button className="text-xs text-[#00d395] hover:text-[#00c584]">
                      DEPOSIT
                    </button>
                    <button className="text-xs text-[#00d395] hover:text-[#00c584]">
                      WITHDRAW
                    </button>
                  </div>
                </td>
              </tr>
            ))
            ) : (
              <tr>
                <td colSpan={9} className="text-center py-8 text-gray-400 text-xs">
                  {loading ? 'Loading balances...' : 'No balances available'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Positions section */}
      {positions.length > 0 ? (
        <>
          <div className="mt-4 px-3 py-2 border-b border-gray-600">
            <h3 className="text-xs font-medium text-gray-400">POSITIONS</h3>
          </div>
          <div className="overflow-x-auto overflow-y-hidden scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-[#2a2d3a]">
            <table className="w-full min-w-[500px]">
              <thead>
                <tr className="border-b border-gray-600">
                  <th className="text-left px-3 py-1 text-xs text-gray-400 font-normal">Market</th>
                  <th 
                    className="text-right px-3 py-1 text-xs text-gray-400 font-normal cursor-pointer hover:text-white transition-colors"
                    onClick={handlePnLSort}
                  >
                    <span className="flex items-center justify-end gap-1">
                      PnL
                      {sortColumn === 'pnl' && (
                        <span className="text-[10px]">
                          {sortDirection === 'desc' ? '▼' : '▲'}
                        </span>
                      )}
                    </span>
                  </th>
                  <th className="text-right px-3 py-1 text-xs text-gray-400 font-normal">Side</th>
                  <th className="text-right px-3 py-1 text-xs text-gray-400 font-normal">Size</th>
                  <th className="text-right px-3 py-1 text-xs text-gray-400 font-normal">Entry</th>
                  <th className="text-right px-3 py-1 text-xs text-gray-400 font-normal">Mark</th>
                </tr>
              </thead>
              <tbody>
                {sortedPositions.map((position) => (
                  <tr 
                    key={`${position.symbol}-${position.side}`} 
                    className="border-b border-gray-700 hover:bg-[#2a2d3a]"
                  >
                    <td className="px-3 py-1 text-xs font-medium">
                      <button
                        onClick={() => setSelectedSymbol(position.symbol)}
                        className="hover:text-[#00d395] hover:underline transition-colors cursor-pointer"
                        title="Click to view market"
                      >
                        {position.symbol}
                      </button>
                    </td>
                    <td className="text-right px-3 py-1">
                      <div className={`text-xs font-mono tabular-nums ${
                        position.unrealized_pnl >= 0 ? 'text-[#00d395]' : 'text-[#f6465d]'
                      }`}>
                        {formatPnL(position.unrealized_pnl)}
                      </div>
                      <div className={`text-xs ${
                        position.percentage >= 0 ? 'text-[#00d395]' : 'text-[#f6465d]'
                      }`}>
                        {formatPercentage(position.percentage)}
                      </div>
                    </td>
                    <td className={`text-right px-3 py-1 text-xs font-medium ${
                      position.side === 'long' ? 'text-[#00d395]' : 'text-[#f6465d]'
                    }`}>
                      {position.side.toUpperCase()}
                    </td>
                    <td className="text-right px-3 py-1 text-xs font-mono tabular-nums">
                      {formatAmount(position.size)}
                    </td>
                    <td className="text-right px-3 py-1 text-xs font-mono tabular-nums">
                      {formatPrice(position.entry_price)}
                    </td>
                    <td className="text-right px-3 py-1 text-xs font-mono tabular-nums">
                      {formatPrice(position.mark_price)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="mt-4 text-center py-8 text-gray-400 text-xs">
          {loading ? 'Loading positions...' : 'No open positions'}
        </div>
      )}
    </div>
  )
}