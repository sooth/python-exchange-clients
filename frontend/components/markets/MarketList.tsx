'use client'

import { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { marketApi } from '@/lib/api'
import { useWebSocketSubscription } from '@/hooks/useWebSocket'
import { useMarket } from '@/contexts/MarketContext'
import type { Ticker } from '@/types/api'

export function MarketList() {
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState('spot')
  const { selectedSymbol, setSelectedSymbol, selectedExchange } = useMarket()
  const [tickerData, setTickerData] = useState<Record<string, Ticker>>({})

  // Fetch initial ticker data
  const { data: tickers = [], isLoading } = useQuery({
    queryKey: ['tickers', selectedExchange],
    queryFn: () => marketApi.getTickers(selectedExchange),
    refetchInterval: 10000,
  })

  // Only subscribe to top markets to avoid exceeding subscription limit
  const topMarkets = useMemo(() => {
    // Sort by volume and take top 30 markets
    return [...tickers]
      .sort((a, b) => {
        const volumeA = parseFloat(a.quote_volume as any) || 0
        const volumeB = parseFloat(b.quote_volume as any) || 0
        return volumeB - volumeA
      })
      .slice(0, 30)
  }, [tickers])

  // Get symbol list for top markets
  const topMarketSymbols = useMemo(() => {
    return topMarkets.map(t => t.symbol)
  }, [topMarkets])

  // Memoize the callback to prevent re-subscriptions
  const handleTickerUpdate = useCallback((symbol: string, data: Ticker) => {
    setTickerData(prev => ({
      ...prev,
      [symbol]: data
    }))
  }, [])

  // Subscribe to real-time ticker updates for top markets only
  useWebSocketSubscription<Ticker>(
    'ticker',
    topMarketSymbols,
    handleTickerUpdate
  )

  // Also subscribe to the selected symbol if it's not in top markets
  const selectedSymbolArray = useMemo(() => {
    if (!selectedSymbol) return []
    const isInTopMarkets = topMarkets.some(t => t.symbol === selectedSymbol)
    return isInTopMarkets ? [] : [selectedSymbol]
  }, [selectedSymbol, topMarkets])

  useWebSocketSubscription<Ticker>(
    'ticker',
    selectedSymbolArray,
    handleTickerUpdate
  )

  // Merge static and real-time data
  const mergedTickers = useMemo(() => {
    return tickers.map(ticker => ({
      ...ticker,
      ...tickerData[ticker.symbol]
    }))
  }, [tickers, tickerData])

  // Filter markets based on search
  const filteredMarkets = useMemo(() => {
    return mergedTickers.filter(ticker =>
      ticker.symbol.toLowerCase().includes(search.toLowerCase())
    )
  }, [mergedTickers, search])

  // Sort by volume (or by symbol if volume is 0)
  const sortedMarkets = useMemo(() => {
    return [...filteredMarkets].sort((a, b) => {
      const volumeA = parseFloat(a.quote_volume as any) || 0
      const volumeB = parseFloat(b.quote_volume as any) || 0
      if (volumeB === 0 && volumeA === 0) {
        return a.symbol.localeCompare(b.symbol)
      }
      return volumeB - volumeA
    })
  }, [filteredMarkets])

  const formatPrice = (price: number | string) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price
    if (isNaN(numPrice)) return '0.00'
    if (numPrice >= 1000) return numPrice.toFixed(0)
    if (numPrice >= 1) return numPrice.toFixed(2)
    if (numPrice >= 0.01) return numPrice.toFixed(4)
    return numPrice.toFixed(6)
  }

  const formatVolume = (volume: number | string) => {
    const numVolume = typeof volume === 'string' ? parseFloat(volume) : volume
    if (isNaN(numVolume)) return '0.00'
    if (numVolume >= 1e9) return `${(numVolume / 1e9).toFixed(2)}B`
    if (numVolume >= 1e6) return `${(numVolume / 1e6).toFixed(2)}M`
    if (numVolume >= 1e3) return `${(numVolume / 1e3).toFixed(2)}K`
    return numVolume.toFixed(2)
  }

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="flex border-b border-gray-600">
        <button 
          onClick={() => setActiveTab('spot')}
          className={`flex-1 px-2 py-2 text-xs font-medium ${
            activeTab === 'spot' ? 'text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Spot
        </button>
        <button 
          onClick={() => setActiveTab('futures')}
          className={`flex-1 px-2 py-2 text-xs font-medium ${
            activeTab === 'futures' ? 'text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Futures
        </button>
        <button 
          onClick={() => setActiveTab('stocks')}
          className={`flex-1 px-2 py-2 text-xs font-medium ${
            activeTab === 'stocks' ? 'text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Stocks
        </button>
      </div>

      {/* Subtabs */}
      <div className="flex border-b border-gray-600 px-2">
        <button className="px-2 py-1.5 text-xs text-white border-b-2 border-[#00d395]">
          FTT
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          SRM
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          BTC
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          ETH
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          BTT
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          OX
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          SLV
        </button>
        <button className="px-2 py-1.5 text-xs text-gray-400 hover:text-white">
          Prediction
        </button>
      </div>

      {/* Search */}
      <div className="p-2 border-b border-gray-600">
        <input
          type="text"
          placeholder="Search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-2 py-1 text-xs bg-[#1a1d29] border border-gray-600 
                     focus:outline-none focus:border-[#00d395] text-white placeholder-gray-500"
        />
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-12 px-2 py-1 border-b border-gray-600 text-xs text-gray-400">
        <div className="col-span-3">Subaccount:</div>
        <div className="col-span-3 text-center">Main Account</div>
        <div className="col-span-2 text-right">SHIFT</div>
        <div className="col-span-2 text-right">SBITH</div>
        <div className="col-span-2 text-right">SHALTS</div>
      </div>

      {/* Market list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-gray-400 text-xs">Loading markets...</div>
        ) : (
          <div>
            {sortedMarkets.map((ticker) => {
              const changePercent = parseFloat(ticker.change_percent as any) || 0
              const isPositive = changePercent >= 0
              
              return (
                <div
                  key={ticker.symbol}
                  className={`grid grid-cols-12 px-2 py-1.5 hover:bg-[#2a2d3a] cursor-pointer transition-colors text-xs ${
                    selectedSymbol === ticker.symbol ? 'bg-[#2a2d3a]' : ''
                  }`}
                  onClick={() => setSelectedSymbol(ticker.symbol)}
                >
                  {/* Symbol */}
                  <div className="col-span-3 font-medium">
                    {ticker.base || ticker.symbol.replace(ticker.quote || 'USDT', '')}/{ticker.quote || 'USDT'}
                  </div>
                  
                  {/* Price */}
                  <div className="col-span-3 text-right font-mono">
                    {formatPrice(ticker.last)}
                  </div>
                  
                  {/* 24h Change */}
                  <div className={`col-span-2 text-right font-mono ${isPositive ? 'text-[#00d395]' : 'text-[#f6465d]'}`}>
                    {isPositive ? '+' : ''}{isNaN(changePercent) ? '0.00' : changePercent.toFixed(2)}%
                  </div>
                  
                  {/* Volume */}
                  <div className="col-span-4 text-right text-gray-400">
                    ${formatVolume(ticker.quote_volume)}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}