'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, UTCTimestamp, IPriceLine } from 'lightweight-charts'
import { marketApi, tradingApi } from '@/lib/api'
import { useMarket } from '@/contexts/MarketContext'
import { getChartWebSocket } from '@/lib/websocket/lmexChartWebSocket'
import { getOrderbookWebSocket, type BestBidAsk } from '@/lib/websocket/lmexOrderbookWebSocket'
import { Candle } from '@/types/market'
import type { CandleResponse } from '@/types/candle'
import type { Position } from '@/types/api'
import { useQuery } from '@tanstack/react-query'
import { useOrderPreview } from '@/contexts/OrderPreviewContext'

interface ChartContainerProps {
  symbol: string
}

export function ChartContainer({ symbol }: ChartContainerProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h')
  const [isLoading, setIsLoading] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const { selectedExchange } = useMarket()
  const { orderPreview } = useOrderPreview()
  const wsRef = useRef<ReturnType<typeof getChartWebSocket> | null>(null)
  const orderbookWsRef = useRef<ReturnType<typeof getOrderbookWebSocket> | null>(null)
  const candleMapRef = useRef<Map<number, any>>(new Map())
  const selectedTimeframeRef = useRef(selectedTimeframe)
  const lastCandleRef = useRef<{ time: number; candle: any & { volume?: number } } | null>(null)
  
  // Position indicator refs
  const positionLineRef = useRef<IPriceLine | null>(null)
  const takeProfitLineRef = useRef<IPriceLine | null>(null)
  const stopLossLineRef = useRef<IPriceLine | null>(null)
  const positionDataRef = useRef<Position | null>(null)
  const currentPriceRef = useRef<number>(0)
  
  // Preview line refs
  const previewEntryLineRef = useRef<IPriceLine | null>(null)
  const previewTakeProfitLineRef = useRef<IPriceLine | null>(null)
  const previewStopLossLineRef = useRef<IPriceLine | null>(null)

  // Fetch symbol info for price precision
  const { data: symbolInfo } = useQuery({
    queryKey: ['symbolInfo', symbol, selectedExchange],
    queryFn: () => marketApi.getSymbolInfo(symbol, selectedExchange),
    staleTime: 60 * 60 * 1000, // Cache for 1 hour
  })

  // Helper function to calculate decimal precision from tick size
  const getPricePrecision = useCallback((tickSize: number): number => {
    if (tickSize === 0) return 2 // Default to 2 decimals
    
    // For values >= 1, precision is 0
    if (tickSize >= 1) return 0
    
    // Convert tick size to string and count decimals
    const tickStr = tickSize.toString()
    const decimalIndex = tickStr.indexOf('.')
    if (decimalIndex === -1) return 0
    
    // Count non-zero decimals
    const decimals = tickStr.substring(decimalIndex + 1)
    // Find the last non-zero digit
    let precision = decimals.length
    for (let i = decimals.length - 1; i >= 0; i--) {
      if (decimals[i] !== '0') {
        precision = i + 1
        break
      }
    }
    
    return precision
  }, [])

  // Update ref when timeframe changes
  useEffect(() => {
    selectedTimeframeRef.current = selectedTimeframe
  }, [selectedTimeframe])

  // WebSocket candle update handler
  const handleCandleUpdate = useCallback((candle: Candle, timeframe: string) => {
    if (timeframe !== selectedTimeframeRef.current) return
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return

    const chartCandle = {
      time: candle.timestamp as UTCTimestamp,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }

    const volumeBar = {
      time: candle.timestamp as UTCTimestamp,
      value: candle.volume,
      color: candle.close >= candle.open ? '#00d39533' : '#dd585833',
    }

    candleSeriesRef.current.update(chartCandle)
    volumeSeriesRef.current.update(volumeBar)
    
    // Update current price for PnL calculations
    currentPriceRef.current = candle.close
  }, []) // Empty deps - uses ref for selectedTimeframe

  // Function to update position line on chart
  const updatePositionLine = useCallback((position: Position | null) => {
    if (!candleSeriesRef.current) return

    // Remove existing lines
    if (positionLineRef.current) {
      candleSeriesRef.current.removePriceLine(positionLineRef.current)
      positionLineRef.current = null
    }
    if (takeProfitLineRef.current) {
      candleSeriesRef.current.removePriceLine(takeProfitLineRef.current)
      takeProfitLineRef.current = null
    }
    if (stopLossLineRef.current) {
      candleSeriesRef.current.removePriceLine(stopLossLineRef.current)
      stopLossLineRef.current = null
    }

    // Add new lines if position exists
    if (position) {
      const isLong = position.side.toLowerCase() === 'long'
      const pnl = typeof position.unrealized_pnl === 'string' ? parseFloat(position.unrealized_pnl) : position.unrealized_pnl
      const pnlFormatted = pnl >= 0 ? `+${pnl.toFixed(2)}` : pnl.toFixed(2)
      
      // Parse entry price
      const entryPrice = typeof position.entry_price === 'string' ? parseFloat(position.entry_price) : position.entry_price
      
      // Get precision for formatting
      let precision = 2
      if (symbolInfo?.tick_size) {
        precision = getPricePrecision(symbolInfo.tick_size)
      }
      
      // Format entry price
      const formattedEntryPrice = entryPrice.toFixed(precision)
      
      // Create position line
      positionLineRef.current = candleSeriesRef.current.createPriceLine({
        price: entryPrice,
        color: isLong ? '#00d395' : '#f6465d',
        lineWidth: 2,
        lineStyle: 2, // Dashed line
        axisLabelVisible: true,
        title: `${position.side.toUpperCase()} ${position.size} @ ${formattedEntryPrice} | PnL: ${pnlFormatted}`,
      })
      
      // Create take profit line if exists
      if (position.take_profit_price) {
        const tpPrice = typeof position.take_profit_price === 'string' ? parseFloat(position.take_profit_price) : position.take_profit_price
        if (tpPrice > 0) {
          const formattedTpPrice = tpPrice.toFixed(precision)
          takeProfitLineRef.current = candleSeriesRef.current.createPriceLine({
            price: tpPrice,
            color: '#00d395', // Green for profit
            lineWidth: 1,
            lineStyle: 2, // Dashed line
            axisLabelVisible: true,
            title: `TP @ ${formattedTpPrice}`,
          })
        }
      }
      
      // Create stop loss line if exists
      if (position.stop_loss_price) {
        const slPrice = typeof position.stop_loss_price === 'string' ? parseFloat(position.stop_loss_price) : position.stop_loss_price
        if (slPrice > 0) {
          const formattedSlPrice = slPrice.toFixed(precision)
          stopLossLineRef.current = candleSeriesRef.current.createPriceLine({
            price: slPrice,
            color: '#f6465d', // Red for loss
            lineWidth: 1,
            lineStyle: 2, // Dashed line
            axisLabelVisible: true,
            title: `SL @ ${formattedSlPrice}`,
          })
        }
      }
    }
    
    positionDataRef.current = position
  }, [symbolInfo, getPricePrecision])

  // Function to update preview lines on chart
  const updatePreviewLines = useCallback(() => {
    if (!candleSeriesRef.current) return
    
    // Only show preview lines for matching symbol and if user has interacted
    if (orderPreview.symbol !== symbol || !orderPreview.hasInteracted) {
      // Remove any existing preview lines if symbol doesn't match
      if (previewEntryLineRef.current) {
        candleSeriesRef.current.removePriceLine(previewEntryLineRef.current)
        previewEntryLineRef.current = null
      }
      if (previewTakeProfitLineRef.current) {
        candleSeriesRef.current.removePriceLine(previewTakeProfitLineRef.current)
        previewTakeProfitLineRef.current = null
      }
      if (previewStopLossLineRef.current) {
        candleSeriesRef.current.removePriceLine(previewStopLossLineRef.current)
        previewStopLossLineRef.current = null
      }
      return
    }

    // Get precision for formatting
    let precision = 2
    if (symbolInfo?.tick_size) {
      precision = getPricePrecision(symbolInfo.tick_size)
    }

    // Update entry preview line
    if (orderPreview.entryPrice && orderPreview.entryPrice > 0) {
      const formattedPrice = orderPreview.entryPrice.toFixed(precision)
      
      if (previewEntryLineRef.current) {
        candleSeriesRef.current.removePriceLine(previewEntryLineRef.current)
      }
      
      previewEntryLineRef.current = candleSeriesRef.current.createPriceLine({
        price: orderPreview.entryPrice,
        color: orderPreview.side === 'buy' ? '#00d39580' : '#f6465d80', // Semi-transparent
        lineWidth: 1,
        lineStyle: 3, // Dotted line
        axisLabelVisible: true,
        title: `Preview Entry: ${formattedPrice}`,
      })
    } else if (previewEntryLineRef.current) {
      candleSeriesRef.current.removePriceLine(previewEntryLineRef.current)
      previewEntryLineRef.current = null
    }

    // Update TP preview line
    if (orderPreview.takeProfitPrice && orderPreview.takeProfitPrice > 0 && orderPreview.placeTakeProfit) {
      const formattedPrice = orderPreview.takeProfitPrice.toFixed(precision)
      
      if (previewTakeProfitLineRef.current) {
        candleSeriesRef.current.removePriceLine(previewTakeProfitLineRef.current)
      }
      
      previewTakeProfitLineRef.current = candleSeriesRef.current.createPriceLine({
        price: orderPreview.takeProfitPrice,
        color: '#00d39550', // Semi-transparent green
        lineWidth: 1,
        lineStyle: 3, // Dotted line
        axisLabelVisible: true,
        title: `Preview TP: ${formattedPrice}`,
      })
    } else if (previewTakeProfitLineRef.current) {
      candleSeriesRef.current.removePriceLine(previewTakeProfitLineRef.current)
      previewTakeProfitLineRef.current = null
    }

    // Update SL preview line
    if (orderPreview.stopLossPrice && orderPreview.stopLossPrice > 0 && orderPreview.placeStopLoss) {
      const formattedPrice = orderPreview.stopLossPrice.toFixed(precision)
      
      if (previewStopLossLineRef.current) {
        candleSeriesRef.current.removePriceLine(previewStopLossLineRef.current)
      }
      
      previewStopLossLineRef.current = candleSeriesRef.current.createPriceLine({
        price: orderPreview.stopLossPrice,
        color: '#f6465d50', // Semi-transparent red
        lineWidth: 1,
        lineStyle: 3, // Dotted line
        axisLabelVisible: true,
        title: `Preview SL: ${formattedPrice}`,
      })
    } else if (previewStopLossLineRef.current) {
      candleSeriesRef.current.removePriceLine(previewStopLossLineRef.current)
      previewStopLossLineRef.current = null
    }
  }, [orderPreview.symbol, orderPreview.side, orderPreview.entryPrice, orderPreview.takeProfitPrice, orderPreview.stopLossPrice, orderPreview.placeTakeProfit, orderPreview.placeStopLoss, orderPreview.hasInteracted, symbol, symbolInfo, getPricePrecision])

  // Fetch positions for current symbol
  const fetchPositions = useCallback(async () => {
    try {
      const positions = await tradingApi.getPositions(selectedExchange)
      const currentPosition = positions.find(p => p.symbol === symbol)
      updatePositionLine(currentPosition || null)
    } catch (error) {
      console.error('Failed to fetch positions:', error)
    }
  }, [symbol, selectedExchange, updatePositionLine])

  useEffect(() => {
    if (!chartContainerRef.current) return

    let chart: IChartApi | null = null
    
    // Create chart
    chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1a1d29' },
        textColor: '#8b8b8b',
      },
      grid: {
        vertLines: { color: '#2a2d3a' },
        horzLines: { color: '#2a2d3a' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#2a2d3a',
          labelBackgroundColor: '#2a2d3a',
        },
        horzLine: {
          color: '#2a2d3a',
          labelBackgroundColor: '#2a2d3a',
        },
      },
      rightPriceScale: {
        borderColor: '#2a2d3a',
      },
      timeScale: {
        borderColor: '#2a2d3a',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    // Add candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00d395',
      downColor: '#f6465d',
      borderVisible: false,
      wickUpColor: '#00d395',
      wickDownColor: '#f6465d',
    })

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    })

    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })

    // Store refs
    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries

    // Handle resize with ResizeObserver for panel resizing
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        try {
          chart.applyOptions({
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
          })
        } catch (error) {
          console.error('Error resizing chart:', error)
        }
      }
    }

    // Use ResizeObserver to handle panel resizing
    const resizeObserver = new ResizeObserver((entries) => {
      // Only resize if chart still exists
      if (chart && chartContainerRef.current) {
        handleResize()
      }
    })
    if (chartContainerRef.current) {
      resizeObserver.observe(chartContainerRef.current)
    }

    // Also handle window resize
    window.addEventListener('resize', handleResize)
    handleResize()

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', handleResize)
      
      // Clean up preview lines
      if (candleSeriesRef.current) {
        if (previewEntryLineRef.current) {
          candleSeriesRef.current.removePriceLine(previewEntryLineRef.current)
          previewEntryLineRef.current = null
        }
        if (previewTakeProfitLineRef.current) {
          candleSeriesRef.current.removePriceLine(previewTakeProfitLineRef.current)
          previewTakeProfitLineRef.current = null
        }
        if (previewStopLossLineRef.current) {
          candleSeriesRef.current.removePriceLine(previewStopLossLineRef.current)
          previewStopLossLineRef.current = null
        }
      }
      
      // Clean up the chart immediately
      if (chart) {
        try {
          chart.remove()
          chart = null
        } catch (e) {
          console.error('Error removing chart:', e)
        }
      }
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [])

  // Fetch and update chart data
  useEffect(() => {
    const fetchChartData = async () => {
      if (!candleSeriesRef.current || !volumeSeriesRef.current) return

      setIsLoading(true)
      try {
        const candles: CandleResponse[] = await marketApi.getCandles(symbol, selectedTimeframe, selectedExchange, 200)
        
        // Transform data for lightweight-charts
        const chartData = candles.map((candle: CandleResponse) => {
          // Parse timestamp - backend sends "2025-07-28T16:00:00" format without timezone
          // Treat as UTC by appending 'Z'
          const timestamp = candle.timestamp.endsWith('Z') ? candle.timestamp : `${candle.timestamp}Z`
          const time = Math.floor(new Date(timestamp).getTime() / 1000) as UTCTimestamp
          
          // Convert string prices to numbers
          return {
            time,
            open: parseFloat(String(candle.open)),
            high: parseFloat(String(candle.high)),
            low: parseFloat(String(candle.low)),
            close: parseFloat(String(candle.close)),
          }
        })

        const volumeData = candles.map((candle: CandleResponse) => {
          // Parse timestamp - backend sends "2025-07-28T16:00:00" format without timezone
          // Treat as UTC by appending 'Z'
          const timestamp = candle.timestamp.endsWith('Z') ? candle.timestamp : `${candle.timestamp}Z`
          const time = Math.floor(new Date(timestamp).getTime() / 1000) as UTCTimestamp
          
          // Convert string values to numbers
          const open = parseFloat(String(candle.open))
          const close = parseFloat(String(candle.close))
          
          return {
            time,
            value: parseFloat(String(candle.volume)),
            color: close >= open ? '#00d39533' : '#dd585833',
          }
        })

        // Update chart
        candleSeriesRef.current.setData(chartData)
        volumeSeriesRef.current.setData(volumeData)

        // Store candles in map for reference
        candleMapRef.current.clear()
        chartData.forEach(candle => {
          candleMapRef.current.set(candle.time, candle)
        })

        // Store the last candle for price updates
        if (chartData.length > 0) {
          const lastCandle = chartData[chartData.length - 1]
          lastCandleRef.current = { time: lastCandle.time, candle: lastCandle }
        }

        // Fit content
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent()
        }
      } catch (error) {
        console.error('Failed to fetch chart data:', error)
        // Fall back to sample data if real data fails
        const sampleData = generateSampleData()
        candleSeriesRef.current.setData(sampleData)
        volumeSeriesRef.current.setData(
          sampleData.map(d => ({
            time: d.time,
            value: d.volume,
            color: d.close >= d.open ? '#00d39533' : '#dd585833',
          }))
        )
      } finally {
        setIsLoading(false)
      }
    }

    fetchChartData()
    
    // Don't use interval refresh when WebSocket is active
  }, [symbol, selectedTimeframe, selectedExchange])

  // WebSocket connection for real-time updates
  useEffect(() => {
    // Only connect WebSocket for LMEX exchange
    if (selectedExchange !== 'lmex') {
      // Clean up if switching away from LMEX
      if (wsRef.current) {
        wsRef.current.disconnect()
        wsRef.current = null
      }
      return
    }

    // Get or create WebSocket instance
    if (!wsRef.current) {
      wsRef.current = getChartWebSocket(true) // true for futures
    }

    const ws = wsRef.current

    // Connect with the stable callback
    ws.connect(
      handleCandleUpdate,
      (error) => {
        console.error('WebSocket error:', error)
      },
      (connected) => {
        setIsConnected(connected)
      }
    )

    // Subscribe to trades for all timeframes
    ws.subscribeToTrades(symbol, ['1m', '5m', '15m', '1h', '4h', '1d'])

    return () => {
      // Unsubscribe when symbol changes or component unmounts
      ws.unsubscribeFromTrades(symbol)
    }
  }, [symbol, selectedExchange, handleCandleUpdate])

  // Rate-limited price update handler
  const priceUpdateQueueRef = useRef<BestBidAsk | null>(null)
  const priceUpdateTimerRef = useRef<NodeJS.Timeout | null>(null)
  const lastUpdateTimeRef = useRef<number>(0)

  // Process queued price update (rate-limited to 250ms)
  const processPriceUpdate = useCallback(() => {
    const bidAsk = priceUpdateQueueRef.current
    if (!bidAsk) return

    console.log('[ChartContainer] Processing price update:', bidAsk)
    
    if (!candleSeriesRef.current || !lastCandleRef.current) {
      console.log('[ChartContainer] Missing refs, skipping update')
      return
    }

    // Use mid price as the last price
    let price = (bidAsk.bid + bidAsk.ask) / 2
    
    if (price <= 0 || isNaN(price)) {
      // Fallback to bid or ask if mid price invalid
      price = bidAsk.bid > 0 ? bidAsk.bid : bidAsk.ask > 0 ? bidAsk.ask : 0
      if (price <= 0) {
        console.log('[ChartContainer] No valid price available')
        return
      }
    }

    // Get current time and timeframe period
    const now = Math.floor(Date.now() / 1000)
    const timeframePeriod = getTimeframePeriod(selectedTimeframeRef.current)
    const currentCandleTime = Math.floor(now / timeframePeriod) * timeframePeriod as UTCTimestamp

    try {
      // Check if we're still in the same candle period
      if (lastCandleRef.current.time === currentCandleTime) {
        // Update the current candle with new price
        const updatedCandle = {
          ...lastCandleRef.current.candle,
          close: price,
          high: Math.max(lastCandleRef.current.candle.high, price),
          low: Math.min(lastCandleRef.current.candle.low, price),
        }
        
        candleSeriesRef.current.update(updatedCandle)
        lastCandleRef.current.candle = updatedCandle
        
        // Update volume bar color based on price direction
        if (volumeSeriesRef.current) {
          const volumeBar = {
            time: currentCandleTime as UTCTimestamp,
            value: lastCandleRef.current.candle.volume || 0,
            color: price >= lastCandleRef.current.candle.open ? '#00d39533' : '#dd585833',
          }
          volumeSeriesRef.current.update(volumeBar)
        }
      } else {
        // Start a new candle
        const newCandle = {
          time: currentCandleTime,
          open: price,
          high: price,
          low: price,
          close: price,
          volume: 0, // Price updates don't include volume
        }
        
        candleSeriesRef.current.update(newCandle)
        lastCandleRef.current = { time: currentCandleTime, candle: newCandle }
        
        // Add new volume bar
        if (volumeSeriesRef.current) {
          const volumeBar = {
            time: currentCandleTime as UTCTimestamp,
            value: 0,
            color: '#00d39533', // Default to green for new candle
          }
          volumeSeriesRef.current.update(volumeBar)
        }
      }

      lastUpdateTimeRef.current = Date.now()
      priceUpdateQueueRef.current = null
    } catch (error) {
      console.error('[ChartContainer] Error updating chart:', error)
      // Don't clear queue on error - retry on next tick
    }
  }, [])

  // Queue price update with rate limiting
  const queuePriceUpdate = useCallback((bidAsk: BestBidAsk) => {
    if (bidAsk.symbol !== symbol) return

    // Store the latest price
    priceUpdateQueueRef.current = bidAsk

    // Clear any existing timer
    if (priceUpdateTimerRef.current) {
      clearTimeout(priceUpdateTimerRef.current)
    }

    // Calculate time since last update
    const timeSinceLastUpdate = Date.now() - lastUpdateTimeRef.current
    const delay = Math.max(0, 250 - timeSinceLastUpdate)

    // Schedule update
    priceUpdateTimerRef.current = setTimeout(processPriceUpdate, delay)
  }, [symbol, processPriceUpdate])

  // Subscribe to orderbook price updates using singleton
  useEffect(() => {
    console.log('[ChartContainer] Price update effect running, exchange:', selectedExchange, 'symbol:', symbol)
    
    // Only connect for LMEX exchange
    if (selectedExchange !== 'lmex') {
      console.log('[ChartContainer] Not LMEX exchange, skipping price updates')
      return
    }

    // Use the singleton orderbook WebSocket
    const ws = getOrderbookWebSocket(true)
    console.log('[ChartContainer] Using singleton orderbook WebSocket for chart')

    // Error recovery timer
    let errorRecoveryTimer: NodeJS.Timeout | null = null
    let healthCheckTimer: NodeJS.Timeout | null = null
    let isSubscribed = false
    let lastHealthCheckTime = Date.now()

    // Health check to ensure updates are still flowing
    const startHealthCheck = () => {
      healthCheckTimer = setInterval(() => {
        const timeSinceLastUpdate = Date.now() - lastUpdateTimeRef.current
        
        if (timeSinceLastUpdate > 10000 && isSubscribed) {
          console.warn('[ChartContainer] No price updates for 10 seconds, checking connection')
          
          // Try to get current price from WebSocket
          const currentPrice = ws.getLastPrice(symbol)
          if (currentPrice !== undefined) {
            console.log('[ChartContainer] Got price from WebSocket cache:', currentPrice)
            // Queue an update with the cached price
            const bidAsk = ws.getBestBidAsk(symbol)
            if (bidAsk) {
              queuePriceUpdate(bidAsk)
            }
          }
          
          // If still no updates after 30 seconds, try resubscribing
          if (timeSinceLastUpdate > 30000) {
            console.error('[ChartContainer] No updates for 30 seconds, attempting recovery')
            ws.unsubscribeFromBestBidAsk(symbol)
            setTimeout(() => {
              if (isSubscribed) {
                ws.subscribeToBestBidAsk(symbol)
              }
            }, 1000)
          }
        }
      }, 5000) // Check every 5 seconds
    }

    const handleConnectionChange = (connected: boolean) => {
      console.log('[ChartContainer] Orderbook WebSocket connection status:', connected)
      
      if (connected && isSubscribed) {
        // Resubscribe on reconnection
        console.log('[ChartContainer] Resubscribing after reconnection')
        ws.subscribeToBestBidAsk(symbol)
        lastHealthCheckTime = Date.now()
      }
    }

    const handleError = (error: Error) => {
      console.error('[ChartContainer] Orderbook WebSocket error:', error)
      
      // Schedule recovery attempt
      if (!errorRecoveryTimer) {
        errorRecoveryTimer = setTimeout(() => {
          console.log('[ChartContainer] Attempting error recovery')
          errorRecoveryTimer = null
          
          // Try to resubscribe
          if (isSubscribed) {
            ws.subscribeToBestBidAsk(symbol)
          }
        }, 5000)
      }
    }

    // Wrap the price update handler to track health
    const handlePriceUpdate = (bidAsk: BestBidAsk) => {
      lastHealthCheckTime = Date.now()
      queuePriceUpdate(bidAsk)
    }

    // Connect and subscribe with error recovery
    ws.connect(handlePriceUpdate, handleError, handleConnectionChange)

    console.log('[ChartContainer] Subscribing to bid/ask for symbol:', symbol)
    ws.subscribeToBestBidAsk(symbol)
    isSubscribed = true
    
    // Start health monitoring
    startHealthCheck()

    return () => {
      console.log('[ChartContainer] Cleaning up orderbook WebSocket subscription')
      isSubscribed = false
      
      // Clear all timers
      if (priceUpdateTimerRef.current) {
        clearTimeout(priceUpdateTimerRef.current)
        priceUpdateTimerRef.current = null
      }
      
      if (errorRecoveryTimer) {
        clearTimeout(errorRecoveryTimer)
      }
      
      if (healthCheckTimer) {
        clearInterval(healthCheckTimer)
      }
      
      ws.unsubscribeFromBestBidAsk(symbol)
      // Don't disconnect - let singleton manage its own lifecycle
    }
  }, [symbol, selectedExchange, queuePriceUpdate])

  // Fetch positions periodically (every 5 seconds)
  useEffect(() => {
    // Initial fetch
    fetchPositions()
    
    // Set up periodic refresh
    const interval = setInterval(fetchPositions, 5000)
    
    return () => clearInterval(interval)
  }, [fetchPositions])

  // Update preview lines when order preview changes
  useEffect(() => {
    updatePreviewLines()
  }, [orderPreview, updatePreviewLines])

  // Helper function to get timeframe period in seconds
  const getTimeframePeriod = (timeframe: string): number => {
    const match = timeframe.match(/^(\d+)([mhd])$/)
    if (!match) return 60 // Default to 1 minute

    const value = parseInt(match[1])
    const unit = match[2]

    switch (unit) {
      case 'm': return value * 60
      case 'h': return value * 3600
      case 'd': return value * 86400
      default: return 60
    }
  }

  return (
    <div className="h-full w-full relative bg-[#1a1d29]">
      <div className="absolute top-2 left-2 z-10 flex items-center space-x-2">
        <div className="flex space-x-1">
          {['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) => (
            <button
              key={tf}
              onClick={() => setSelectedTimeframe(tf)}
              className={`px-2 py-1 text-xs transition-colors ${
                selectedTimeframe === tf
                  ? 'text-white bg-[#2a2d3a]'
                  : 'text-gray-400 hover:text-white hover:bg-[#2a2d3a]'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
        {isLoading && (
          <div className="text-xs text-gray-400 animate-pulse">Loading...</div>
        )}
        {!isLoading && isConnected && selectedExchange === 'lmex' && (
          <div className="flex items-center space-x-1 text-xs text-green-500">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Live</span>
          </div>
        )}
      </div>
      <div ref={chartContainerRef} className="h-full w-full" />
    </div>
  )
}

// Generate sample candlestick data
function generateSampleData() {
  const data = []
  const now = Math.floor(Date.now() / 1000)
  let price = 40000 + Math.random() * 5000

  for (let i = 100; i >= 0; i--) {
    const time = now - i * 3600 // 1 hour intervals
    const open = price
    const change = (Math.random() - 0.5) * 1000
    price = price + change
    const close = price
    const high = Math.max(open, close) + Math.random() * 200
    const low = Math.min(open, close) - Math.random() * 200
    const volume = 1000000 + Math.random() * 5000000

    data.push({
      time: time as UTCTimestamp,
      open,
      high,
      low,
      close,
      volume,
    })
  }

  return data
}