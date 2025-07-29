'use client'

import { useState, useEffect, useMemo } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { tradingApi, marketApi, accountApi } from '@/lib/api'
import toast from 'react-hot-toast'
import type { CreateOrderRequest, OrderType, OrderSide } from '@/types/api'

interface OrderFormProps {
  symbol: string
  exchange?: string
}

// Custom checkbox component
function CustomCheckbox({ 
  checked, 
  onChange,
  disabled = false 
}: { 
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
        checked 
          ? 'bg-[#00d395] border-[#00d395]' 
          : 'bg-transparent border-gray-600 hover:border-gray-500'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      {checked && (
        <svg className="w-2.5 h-2.5 text-black" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      )}
    </button>
  )
}

export function OrderFormV3({ symbol, exchange }: OrderFormProps) {
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [entryPrice, setEntryPrice] = useState('')
  const [orderType, setOrderType] = useState<'Market' | 'Limit'>('Market')
  const [takeProfitPrice, setTakeProfitPrice] = useState('')
  const [takeProfitPercent, setTakeProfitPercent] = useState('5')
  const [stopLossPrice, setStopLossPrice] = useState('')
  const [stopLossPercent, setStopLossPercent] = useState('1.5')
  const [amount, setAmount] = useState('1')
  const [amountInUSD, setAmountInUSD] = useState('')
  const [takeProfitReduce, setTakeProfitReduce] = useState(true)
  const [stopLossReduce, setStopLossReduce] = useState(true)
  const [placeTakeProfit, setPlaceTakeProfit] = useState(true)
  const [placeStopLoss, setPlaceStopLoss] = useState(true)

  // Fetch current market price
  const { data: ticker } = useQuery({
    queryKey: ['ticker', symbol, exchange],
    queryFn: () => marketApi.getTicker(symbol, exchange),
    refetchInterval: 5000,
  })

  // Use market price for entry when market order
  const currentPrice = parseFloat(ticker?.last || '0')
  const effectiveEntryPrice = orderType === 'Market' ? currentPrice : parseFloat(entryPrice || '0')

  // Update entry price when switching to market
  useEffect(() => {
    if (orderType === 'Market' && currentPrice > 0) {
      setEntryPrice(currentPrice.toFixed(2))
    }
  }, [orderType, currentPrice])

  // Handle TP percentage change -> update price
  const handleTakeProfitPercentChange = (value: string) => {
    setTakeProfitPercent(value)
    if (effectiveEntryPrice > 0 && value) {
      const percent = parseFloat(value) / 100
      const price = side === 'buy' 
        ? effectiveEntryPrice * (1 + percent)
        : effectiveEntryPrice * (1 - percent)
      setTakeProfitPrice(price.toFixed(2))
    }
  }

  // Handle TP price change -> update percentage
  const handleTakeProfitPriceChange = (value: string) => {
    setTakeProfitPrice(value)
    if (effectiveEntryPrice > 0 && value) {
      const price = parseFloat(value)
      let percent = 0
      if (side === 'buy') {
        percent = ((price - effectiveEntryPrice) / effectiveEntryPrice) * 100
      } else {
        percent = ((effectiveEntryPrice - price) / effectiveEntryPrice) * 100
      }
      setTakeProfitPercent(Math.abs(percent).toFixed(1))
    }
  }

  // Handle SL percentage change -> update price
  const handleStopLossPercentChange = (value: string) => {
    setStopLossPercent(value)
    if (effectiveEntryPrice > 0 && value) {
      const percent = parseFloat(value) / 100
      const price = side === 'buy' 
        ? effectiveEntryPrice * (1 - percent)
        : effectiveEntryPrice * (1 + percent)
      setStopLossPrice(price.toFixed(2))
    }
  }

  // Handle SL price change -> update percentage
  const handleStopLossPriceChange = (value: string) => {
    setStopLossPrice(value)
    if (effectiveEntryPrice > 0 && value) {
      const price = parseFloat(value)
      let percent = 0
      if (side === 'buy') {
        percent = ((effectiveEntryPrice - price) / effectiveEntryPrice) * 100
      } else {
        percent = ((price - effectiveEntryPrice) / effectiveEntryPrice) * 100
      }
      setStopLossPercent(Math.abs(percent).toFixed(1))
    }
  }

  // Initialize TP/SL when entry price or side changes
  useEffect(() => {
    if (effectiveEntryPrice > 0) {
      // Only update if fields are empty (initial load)
      if (!takeProfitPrice) {
        handleTakeProfitPercentChange(takeProfitPercent)
      }
      if (!stopLossPrice) {
        handleStopLossPercentChange(stopLossPercent)
      }
    }
  }, [effectiveEntryPrice, side])

  // Handle amount change -> update USD
  const handleAmountChange = (value: string) => {
    setAmount(value)
    if (effectiveEntryPrice > 0 && value) {
      const assetAmount = parseFloat(value)
      const usdValue = assetAmount * effectiveEntryPrice
      setAmountInUSD(usdValue.toFixed(2))
    }
  }

  // Handle USD amount change -> update asset amount
  const handleAmountInUSDChange = (value: string) => {
    setAmountInUSD(value)
    if (effectiveEntryPrice > 0 && value) {
      const usdValue = parseFloat(value)
      const assetAmount = usdValue / effectiveEntryPrice
      setAmount(assetAmount.toFixed(4))
    }
  }

  // Initialize amount when entry price changes
  useEffect(() => {
    if (effectiveEntryPrice > 0) {
      // If we have an amount but no USD value, calculate USD
      if (amount && !amountInUSD) {
        const usdValue = parseFloat(amount) * effectiveEntryPrice
        setAmountInUSD(usdValue.toFixed(2))
      }
      // If we have USD but no amount, calculate amount
      else if (amountInUSD && !amount) {
        const usdValue = parseFloat(amountInUSD)
        const assetAmount = usdValue / effectiveEntryPrice
        setAmount(assetAmount.toFixed(4))
      }
    }
  }, [effectiveEntryPrice])

  // PnL Calculations
  const calculations = useMemo(() => {
    const entryPriceNum = effectiveEntryPrice
    const tpPriceNum = parseFloat(takeProfitPrice || '0')
    const slPriceNum = parseFloat(stopLossPrice || '0')
    const amountNum = parseFloat(amount || '0')

    if (entryPriceNum === 0 || amountNum === 0) {
      return { exitPnL: 0, stopPnL: 0, riskReward: 0 }
    }

    let exitPnL = 0
    let stopPnL = 0

    if (side === 'buy') {
      exitPnL = (tpPriceNum - entryPriceNum) * amountNum
      stopPnL = (slPriceNum - entryPriceNum) * amountNum
    } else {
      exitPnL = (entryPriceNum - tpPriceNum) * amountNum
      stopPnL = (entryPriceNum - slPriceNum) * amountNum
    }

    const riskReward = Math.abs(stopPnL) > 0 ? Math.abs(exitPnL / stopPnL) : 0

    return { exitPnL, stopPnL, riskReward }
  }, [effectiveEntryPrice, takeProfitPrice, stopLossPrice, amount, side])

  // Place order mutation
  const placeOrderMutation = useMutation({
    mutationFn: async () => {
      const orders: CreateOrderRequest[] = []

      // Main entry order
      const mainOrder: CreateOrderRequest = {
        symbol,
        side,
        type: orderType.toLowerCase() as OrderType,
        amount: parseFloat(amount),
        price: orderType === 'Limit' ? effectiveEntryPrice : undefined,
      }
      orders.push(mainOrder)

      // Place all orders
      const results = await Promise.all(
        orders.map(order => tradingApi.placeOrder(order, exchange))
      )

      // If successful, place TP/SL orders
      if (placeTakeProfit || placeStopLoss) {
        const tpslOrders: CreateOrderRequest[] = []

        if (placeTakeProfit && takeProfitPrice) {
          tpslOrders.push({
            symbol,
            side: side === 'buy' ? 'sell' : 'buy',
            type: 'take_profit_limit',
            amount: parseFloat(amount),
            price: parseFloat(takeProfitPrice),
            stop_price: parseFloat(takeProfitPrice),
            reduce_only: takeProfitReduce,
          })
        }

        if (placeStopLoss && stopLossPrice) {
          tpslOrders.push({
            symbol,
            side: side === 'buy' ? 'sell' : 'buy',
            type: 'stop',
            amount: parseFloat(amount),
            stop_price: parseFloat(stopLossPrice),
            reduce_only: stopLossReduce,
          })
        }

        if (tpslOrders.length > 0) {
          await Promise.all(
            tpslOrders.map(order => tradingApi.placeOrder(order, exchange))
          )
        }
      }

      return results
    },
    onSuccess: () => {
      toast.success('Orders placed successfully')
      // Reset form
      setAmount('1')
      setTakeProfitPercent('5')
      setStopLossPercent('1.5')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to place orders')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    placeOrderMutation.mutate()
  }

  const baseAsset = symbol.replace('-PERP', '').replace('/USDT', '')

  return (
    <form onSubmit={handleSubmit} className="h-full flex flex-col bg-[#1a1d29]">
      {/* Header with settings */}
      <div className="absolute top-2 right-2 z-10">
        <button type="button" className="p-1 text-gray-400 hover:text-gray-300">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m4.22-10.22l1.42-1.42M6.36 17.64l1.42 1.42M1 12h6m6 0h6m-2.22-4.22l1.42 1.42M6.36 6.36l1.42-1.42"></path>
          </svg>
        </button>
      </div>

      {/* Buy/Sell tabs */}
      <div className="flex">
        <button
          type="button"
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            side === 'buy'
              ? 'bg-[#00d395] text-black'
              : 'bg-[#2a2d3a] text-gray-400 hover:text-gray-300'
          }`}
          onClick={() => setSide('buy')}
        >
          Buy {baseAsset}-PERP
        </button>
        <button
          type="button"
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            side === 'sell'
              ? 'bg-[#f6465d] text-white'
              : 'bg-[#2a2d3a] text-gray-400 hover:text-gray-300'
          }`}
          onClick={() => setSide('sell')}
        >
          Sell {baseAsset}-PERP
        </button>
      </div>

      <div className="flex-1 px-4 py-3 space-y-4 overflow-y-auto">
        {/* Entry price */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">Market entry</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              disabled={orderType === 'Market'}
              className="flex-1 px-3 py-1.5 bg-[#2a2d3a] rounded text-white text-sm disabled:opacity-50"
              step="0.01"
            />
            <span className="px-2 py-1 bg-[#2a2d3a] text-xs text-gray-300 rounded">USD</span>
            <span className="text-xs text-gray-500">≈</span>
            <div className="relative w-[120px]">
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as 'Market' | 'Limit')}
                className="w-full px-2 py-1.5 pr-8 bg-[#2a2d3a] rounded text-center text-white text-sm appearance-none cursor-pointer"
              >
                <option value="Market">Market</option>
                <option value="Limit">Limit</option>
              </select>
              <svg className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        {/* Take profit exit */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">Take profit exit</span>
            <span className="text-[10px] text-gray-500">Reduce</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={takeProfitPrice}
              onChange={(e) => handleTakeProfitPriceChange(e.target.value)}
              className="flex-1 px-3 py-1.5 bg-[#2a2d3a] rounded text-white text-sm"
              step="0.01"
              disabled={!placeTakeProfit}
            />
            <span className="px-2 py-1 bg-[#2a2d3a] text-xs text-gray-300 rounded">USD</span>
            <span className="text-xs text-gray-500">≈</span>
            <input
              type="number"
              value={takeProfitPercent}
              onChange={(e) => handleTakeProfitPercentChange(e.target.value)}
              className="w-16 px-2 py-1.5 bg-[#2a2d3a] rounded text-right text-white text-sm"
              step="0.1"
              disabled={!placeTakeProfit}
            />
            <span className="text-xs text-gray-500">%</span>
            <CustomCheckbox
              checked={takeProfitReduce}
              onChange={setTakeProfitReduce}
              disabled={!placeTakeProfit}
            />
          </div>
        </div>

        {/* Stop loss */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">Stop loss</span>
            <span className="text-[10px] text-gray-500">Reduce</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={stopLossPrice}
              onChange={(e) => handleStopLossPriceChange(e.target.value)}
              className="flex-1 px-3 py-1.5 bg-[#2a2d3a] rounded text-white text-sm"
              step="0.01"
              disabled={!placeStopLoss}
            />
            <span className="px-2 py-1 bg-[#2a2d3a] text-xs text-gray-300 rounded">USD</span>
            <span className="text-xs text-gray-500">≈</span>
            <input
              type="number"
              value={stopLossPercent}
              onChange={(e) => handleStopLossPercentChange(e.target.value)}
              className="w-16 px-2 py-1.5 bg-[#2a2d3a] rounded text-right text-white text-sm"
              step="0.1"
              disabled={!placeStopLoss}
            />
            <span className="text-xs text-gray-500">%</span>
            <CustomCheckbox
              checked={stopLossReduce}
              onChange={setStopLossReduce}
              disabled={!placeStopLoss}
            />
          </div>
        </div>

        {/* Amount */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">Amount</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={amount}
              onChange={(e) => handleAmountChange(e.target.value)}
              className="flex-1 px-3 py-1.5 bg-[#2a2d3a] rounded text-white text-sm"
              step="0.001"
            />
            <span className="px-2 py-1 bg-[#2a2d3a] text-xs text-gray-300 rounded">{baseAsset}</span>
            <span className="text-xs text-gray-500">≈</span>
            <input
              type="number"
              value={amountInUSD}
              onChange={(e) => handleAmountInUSDChange(e.target.value)}
              className="w-24 px-2 py-1.5 bg-[#2a2d3a] rounded text-right text-white text-sm"
              step="0.01"
            />
            <span className="px-2 py-1 bg-[#2a2d3a] text-xs text-gray-300 rounded mr-2">USD</span>
          </div>
        </div>

        {/* PnL calculations */}
        <div className="grid grid-cols-3 gap-2 p-3 bg-[#2a2d3a] rounded">
          <div className="text-center">
            <div className="text-base font-medium text-[#00d395]">
              {calculations.exitPnL >= 0 ? '+' : ''}{calculations.exitPnL.toFixed(2)} USD
            </div>
            <div className="text-[10px] text-gray-400">Exit PnL</div>
          </div>
          <div className="text-center border-x border-gray-600">
            <div className="text-base font-medium text-[#f6465d]">
              {calculations.stopPnL.toFixed(2)} USD
            </div>
            <div className="text-[10px] text-gray-400">Stop PnL</div>
          </div>
          <div className="text-center">
            <div className="text-base font-medium text-white">
              {calculations.riskReward.toFixed(2)}x
            </div>
            <div className="text-[10px] text-gray-400">Risk-Reward</div>
          </div>
        </div>

        {/* Order summary */}
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-400">Entry Order</span>
            <span className="text-gray-300">{side === 'buy' ? 'Buy' : 'Sell'}, {orderType.toLowerCase()}</span>
          </div>
          {placeTakeProfit && (
            <div className="flex justify-between">
              <span className="text-gray-400">Take Profit</span>
              <span className="text-gray-300">{side === 'buy' ? 'Sell' : 'Buy'}, triggers at {takeProfitPrice} USD {takeProfitReduce && '(Reduce)'}</span>
            </div>
          )}
          {placeStopLoss && (
            <div className="flex justify-between">
              <span className="text-gray-400">Stop Loss</span>
              <span className="text-gray-300">{side === 'buy' ? 'Sell' : 'Buy'}, triggers at {stopLossPrice} USD {stopLossReduce && '(Reduce)'}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-gray-400">Size</span>
            <span className="text-gray-300">{amount} {baseAsset}-PERP</span>
          </div>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={placeOrderMutation.isPending}
          className="w-full py-3 text-xs font-medium bg-[#00d395] text-black hover:bg-[#00c584] 
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors uppercase tracking-wider"
        >
          {placeOrderMutation.isPending ? 'PLACING ORDERS...' : 'PLACE ORDERS'}
        </button>
      </div>
    </form>
  )
}