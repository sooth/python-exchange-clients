'use client'

import { useState, useEffect, useMemo } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { tradingApi, marketApi, accountApi } from '@/lib/api'
import toast from 'react-hot-toast'
import type { CreateOrderRequest, OrderType, OrderSide } from '@/types/api'

interface ApiError {
  response?: {
    data?: {
      detail?: string
    }
  }
}

interface OrderFormProps {
  symbol: string
  exchange?: string
}

// Custom checkbox component
function CustomCheckbox({ checked, onChange, className = '' }: { 
  checked: boolean
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  className?: string 
}) {
  return (
    <div className={`relative ${className}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only"
      />
      <div className={`w-4 h-4 rounded border-2 cursor-pointer transition-all ${
        checked 
          ? 'bg-[#00d395] border-[#00d395]' 
          : 'bg-transparent border-gray-600'
      }`}>
        {checked && (
          <svg className="w-3 h-3 text-black" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )}
      </div>
    </div>
  )
}

export function OrderFormV2({ symbol, exchange }: OrderFormProps) {
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

  // Fetch account balance
  const { data: accountInfo } = useQuery({
    queryKey: ['balance', exchange],
    queryFn: () => accountApi.getBalance(exchange),
    refetchInterval: 10000,
  })

  // Fetch symbol info for validation
  const { data: symbolInfo } = useQuery({
    queryKey: ['symbolInfo', symbol, exchange],
    queryFn: () => marketApi.getSymbolInfo(symbol, exchange),
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

  // Calculate TP/SL prices based on percentages
  useEffect(() => {
    if (effectiveEntryPrice > 0) {
      const tpPercent = parseFloat(takeProfitPercent || '0') / 100
      const slPercent = parseFloat(stopLossPercent || '0') / 100

      if (side === 'buy') {
        const tpPrice = effectiveEntryPrice * (1 + tpPercent)
        const slPrice = effectiveEntryPrice * (1 - slPercent)
        setTakeProfitPrice(tpPrice.toFixed(2))
        setStopLossPrice(slPrice.toFixed(2))
      } else {
        const tpPrice = effectiveEntryPrice * (1 - tpPercent)
        const slPrice = effectiveEntryPrice * (1 + slPercent)
        setTakeProfitPrice(tpPrice.toFixed(2))
        setStopLossPrice(slPrice.toFixed(2))
      }
    }
  }, [effectiveEntryPrice, takeProfitPercent, stopLossPercent, side])

  // Calculate amount in USD
  useEffect(() => {
    if (effectiveEntryPrice > 0 && amount) {
      const usdValue = parseFloat(amount) * effectiveEntryPrice
      setAmountInUSD(usdValue.toFixed(2))
    }
  }, [effectiveEntryPrice, amount])

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
    onError: (error: ApiError) => {
      toast.error(error.response?.data?.detail || 'Failed to place orders')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount')
      return
    }

    if (orderType === 'Limit' && (!entryPrice || parseFloat(entryPrice) <= 0)) {
      toast.error('Please enter a valid entry price')
      return
    }

    placeOrderMutation.mutate()
  }

  const baseAsset = symbol.replace('-PERP', '').replace('/USDT', '')

  return (
    <form onSubmit={handleSubmit} className="h-full flex flex-col bg-[#1a1d29]">
      {/* Buy/Sell tabs */}
      <div className="flex">
        <button
          type="button"
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            side === 'buy'
              ? 'bg-[#00d395] text-black'
              : 'bg-[#2a2d3a] text-gray-400'
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
              : 'bg-[#2a2d3a] text-gray-400'
          }`}
          onClick={() => setSide('sell')}
        >
          Sell {baseAsset}-PERP
        </button>
      </div>

      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Entry price */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Entry price *</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">USD</span>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as 'Market' | 'Limit')}
                className="bg-background-secondary text-sm px-2 py-1 rounded"
              >
                <option value="Market">Market</option>
                <option value="Limit">Limit</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">MKT</span>
            <input
              type="number"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              disabled={orderType === 'Market'}
              className="flex-1 px-3 py-2 bg-background-secondary rounded text-lg font-medium"
              step="0.01"
            />
          </div>
        </div>

        {/* Take profit exit */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Take profit exit</span>
            <div className="flex items-center gap-4">
              <span className="text-xs text-text-secondary">% Gain</span>
              <label className="flex items-center gap-2 text-xs text-gray-400">
                <span>Reduce</span>
                <CustomCheckbox
                  checked={takeProfitReduce}
                  onChange={(e) => setTakeProfitReduce(e.target.checked)}
                />
              </label>
              <CustomCheckbox
                checked={placeTakeProfit}
                onChange={(e) => setPlaceTakeProfit(e.target.checked)}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={takeProfitPrice}
              onChange={(e) => setTakeProfitPrice(e.target.value)}
              className="flex-1 px-3 py-2 bg-background-secondary rounded text-white"
              step="0.01"
              disabled={!placeTakeProfit}
            />
            <span className="text-xs text-text-secondary px-2 py-1 bg-background-secondary rounded">USD</span>
            <span className="text-sm text-text-secondary">≈</span>
            <input
              type="number"
              value={takeProfitPercent}
              onChange={(e) => setTakeProfitPercent(e.target.value)}
              className="w-20 px-3 py-2 bg-background-secondary rounded text-right text-white"
              step="0.1"
              disabled={!placeTakeProfit}
            />
            <span className="text-sm text-text-secondary">%</span>
          </div>
        </div>

        {/* Stop loss */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Stop loss</span>
            <div className="flex items-center gap-4">
              <span className="text-sm text-text-secondary">% Loss</span>
              <label className="flex items-center gap-2">
                <span className="text-xs text-text-secondary">Reduce</span>
                <input
                  type="checkbox"
                  checked={stopLossReduce}
                  onChange={(e) => setStopLossReduce(e.target.checked)}
                  className="w-4 h-4"
                />
              </label>
              <input
                type="checkbox"
                checked={placeStopLoss}
                onChange={(e) => setPlaceStopLoss(e.target.checked)}
                className="w-4 h-4"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={stopLossPrice}
              onChange={(e) => setStopLossPrice(e.target.value)}
              className="flex-1 px-3 py-2 bg-background-secondary rounded"
              step="0.01"
              disabled={!placeStopLoss}
            />
            <span className="text-sm text-text-secondary">USD</span>
            <span className="text-sm text-text-secondary">≈</span>
            <input
              type="number"
              value={stopLossPercent}
              onChange={(e) => setStopLossPercent(e.target.value)}
              className="w-20 px-3 py-2 bg-background-secondary rounded text-right"
              step="0.1"
              disabled={!placeStopLoss}
            />
            <span className="text-sm text-text-secondary">%</span>
          </div>
        </div>

        {/* Amount */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Amount</span>
            <span className="text-sm text-text-secondary">Amount</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="flex-1 px-3 py-2 bg-background-secondary rounded"
              step={symbolInfo?.lot_size || 0.001}
            />
            <span className="text-sm text-text-secondary">{baseAsset}</span>
            <span className="text-sm text-text-secondary">≈</span>
            <input
              type="number"
              value={amountInUSD}
              onChange={(e) => {
                const usdValue = parseFloat(e.target.value || '0')
                if (effectiveEntryPrice > 0) {
                  setAmount((usdValue / effectiveEntryPrice).toFixed(4))
                }
              }}
              className="flex-1 px-3 py-2 bg-background-secondary rounded"
              step="0.01"
            />
            <span className="text-sm text-text-secondary">USD</span>
          </div>
        </div>

        {/* PnL calculations */}
        <div className="grid grid-cols-3 gap-2 p-3 bg-background-secondary rounded">
          <div className="text-center">
            <div className="text-lg font-medium">
              {calculations.exitPnL >= 0 ? '+' : ''}{calculations.exitPnL.toFixed(2)} USD
            </div>
            <div className="text-xs text-text-secondary">Exit PnL</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-medium text-error">
              {calculations.stopPnL.toFixed(2)} USD
            </div>
            <div className="text-xs text-text-secondary">Stop PnL</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-medium">
              {calculations.riskReward.toFixed(2)}x
            </div>
            <div className="text-xs text-text-secondary">Risk-Reward</div>
          </div>
        </div>

        {/* Order summary */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Entry Order</span>
            <span>{side === 'buy' ? 'Buy' : 'Sell'}, {orderType.toLowerCase()}</span>
          </div>
          {placeTakeProfit && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Take Profit</span>
              <span>{side === 'buy' ? 'Sell' : 'Buy'}, triggers at {takeProfitPrice} USD {takeProfitReduce && '(Reduce)'}</span>
            </div>
          )}
          {placeStopLoss && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Stop Loss</span>
              <span>{side === 'buy' ? 'Sell' : 'Buy'}, triggers at {stopLossPrice} USD {stopLossReduce && '(Reduce)'}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-text-secondary">Size</span>
            <span>{amount} {baseAsset}-PERP</span>
          </div>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={placeOrderMutation.isPending}
          className="w-full py-3 text-sm font-medium bg-success text-black hover:brightness-110 
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {placeOrderMutation.isPending ? 'PLACING ORDERS...' : 'PLACE ORDERS'}
        </button>
      </div>
    </form>
  )
}