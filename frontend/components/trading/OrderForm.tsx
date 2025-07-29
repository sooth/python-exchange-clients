'use client'

import { useState } from 'react'
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

export function OrderForm({ symbol, exchange }: OrderFormProps) {
  const [side, setSide] = useState<OrderSide>('buy')
  const [orderType, setOrderType] = useState<OrderType>('limit')
  const [price, setPrice] = useState('')
  const [amount, setAmount] = useState('')
  const [reduceOnly, setReduceOnly] = useState(false)
  const [postOnly, setPostOnly] = useState(false)
  const [ioc, setIoc] = useState(false)
  const [leverage, setLeverage] = useState(1)

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

  // Place order mutation
  const placeOrderMutation = useMutation({
    mutationFn: (order: CreateOrderRequest) => tradingApi.placeOrder(order, exchange),
    onSuccess: () => {
      toast.success('Order placed successfully')
      // Reset form
      setPrice('')
      setAmount('')
    },
    onError: (error: ApiError) => {
      toast.error(error.response?.data?.detail || 'Failed to place order')
    },
  })

  const handlePriceChange = (value: string) => {
    setPrice(value)
  }

  const handleAmountChange = (value: string) => {
    setAmount(value)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!amount || (orderType === 'limit' && !price)) {
      toast.error('Please fill in all required fields')
      return
    }

    const order: CreateOrderRequest = {
      symbol,
      side,
      type: orderType,
      amount: parseFloat(amount),
      price: orderType === 'limit' ? parseFloat(price) : undefined,
    }

    placeOrderMutation.mutate(order)
  }

  const availableBalance = accountInfo?.balances?.USDT?.free || '0'

  return (
    <form onSubmit={handleSubmit} className="h-full flex flex-col bg-background-primary">
      {/* Header with leverage */}
      <div className="px-3 py-2 border-b border-border-primary flex items-center justify-between">
        <span className="text-xs text-text-secondary">LEVERAGE</span>
        <div className="flex items-center space-x-2">
          <button type="button" className="text-xs text-accent-primary">-</button>
          <span className="text-sm font-medium px-2">{leverage}x</span>
          <button type="button" className="text-xs text-accent-primary">+</button>
        </div>
      </div>

      <div className="flex-1 px-3 py-2 space-y-3">
        {/* Buy/Sell tabs */}
        <div className="flex space-x-1">
          <button
            type="button"
            className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
              side === 'buy'
                ? 'bg-success text-background-primary'
                : 'bg-background-tertiary text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => setSide('buy')}
          >
            BUY / LONG
          </button>
          <button
            type="button"
            className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
              side === 'sell'
                ? 'bg-error text-white'
                : 'bg-background-tertiary text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => setSide('sell')}
          >
            SELL / SHORT
          </button>
        </div>

        {/* Order type tabs */}
        <div className="flex space-x-2 text-xs">
          <button
            type="button"
            onClick={() => setOrderType('limit')}
            className={`${orderType === 'limit' ? 'text-text-primary' : 'text-text-secondary'} hover:text-text-primary`}
          >
            Limit
          </button>
          <button
            type="button"
            onClick={() => setOrderType('market')}
            className={`${orderType === 'market' ? 'text-text-primary' : 'text-text-secondary'} hover:text-text-primary`}
          >
            Market
          </button>
          <button
            type="button"
            onClick={() => setOrderType('stop')}
            className={`${orderType === 'stop' ? 'text-text-primary' : 'text-text-secondary'} hover:text-text-primary`}
          >
            Stop Market
          </button>
          <button
            type="button"
            onClick={() => setOrderType('stop_limit')}
            className={`${orderType === 'stop_limit' ? 'text-text-primary' : 'text-text-secondary'} hover:text-text-primary`}
          >
            Stop Limit
          </button>
          <button
            type="button"
            className="text-text-secondary hover:text-text-primary"
          >
            Trailing Stop
          </button>
        </div>

        {/* Price input (for limit orders) */}
        {(orderType === 'limit' || orderType === 'stop_limit') && (
          <div>
            <div className="flex items-center justify-between text-xs text-text-secondary mb-1">
              <span>Limit Price</span>
              <span>USD</span>
            </div>
            <input
              type="number"
              value={price}
              onChange={(e) => handlePriceChange(e.target.value)}
              placeholder="0.00"
              step={symbolInfo?.tick_size || 0.01}
              className="w-full px-2 py-1.5 bg-background-secondary border border-border-primary text-sm 
                         focus:outline-none focus:border-accent-primary text-text-primary placeholder-text-muted"
            />
          </div>
        )}

        {/* Amount input */}
        <div>
          <div className="flex items-center justify-between text-xs text-text-secondary mb-1">
            <span>Amount</span>
            <span>{symbol.replace('USDT', '')}</span>
          </div>
          <input
            type="number"
            value={amount}
            onChange={(e) => handleAmountChange(e.target.value)}
            placeholder="0.00"
            step={symbolInfo?.lot_size || 0.001}
            className="w-full px-2 py-1.5 bg-background-secondary border border-border-primary text-sm 
                       focus:outline-none focus:border-accent-primary text-text-primary placeholder-text-muted"
          />
        </div>

        {/* Total display */}
        {orderType === 'limit' && price && amount && (
          <div>
            <div className="flex items-center justify-between text-xs text-text-secondary mb-1">
              <span>Total</span>
              <span>USD</span>
            </div>
            <div className="px-2 py-1.5 bg-background-secondary border border-border-primary text-sm">
              {(parseFloat(price || '0') * parseFloat(amount || '0')).toFixed(2)}
            </div>
          </div>
        )}

        {/* Options */}
        <div className="space-y-2">
          <label className="flex items-center space-x-2 text-xs">
            <input
              type="checkbox"
              checked={reduceOnly}
              onChange={(e) => setReduceOnly(e.target.checked)}
              className="w-3 h-3"
            />
            <span className="text-text-secondary">Reduce Only</span>
          </label>
          {orderType === 'limit' && (
            <>
              <label className="flex items-center space-x-2 text-xs">
                <input
                  type="checkbox"
                  checked={postOnly}
                  onChange={(e) => setPostOnly(e.target.checked)}
                  className="w-3 h-3"
                />
                <span className="text-text-secondary">Post Only</span>
              </label>
              <label className="flex items-center space-x-2 text-xs">
                <input
                  type="checkbox"
                  checked={ioc}
                  onChange={(e) => setIoc(e.target.checked)}
                  className="w-3 h-3"
                />
                <span className="text-text-secondary">IOC</span>
              </label>
            </>
          )}
        </div>

        {/* Available balance */}
        <div className="text-xs">
          <div className="flex justify-between">
            <span className="text-text-secondary">Max</span>
            <span className="text-text-primary">{parseFloat(availableBalance || '0').toFixed(2)} USD</span>
          </div>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={placeOrderMutation.isPending}
          className={`w-full py-2 text-sm font-medium transition-colors ${
            side === 'buy'
              ? 'bg-success hover:brightness-110 text-background-primary'
              : 'bg-error hover:brightness-110 text-white'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {placeOrderMutation.isPending
            ? 'Placing Order...'
            : orderType === 'market' 
              ? `Market ${side === 'buy' ? 'Buy' : 'Sell'}`
              : `Place ${side === 'buy' ? 'Buy' : 'Sell'} Order`}
        </button>
      </div>
    </form>
  )
}