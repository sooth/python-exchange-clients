'use client'

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface OrderPreviewData {
  symbol: string
  side: 'buy' | 'sell' | null
  entryPrice: number | null
  takeProfitPrice: number | null
  stopLossPrice: number | null
  placeTakeProfit: boolean
  placeStopLoss: boolean
  hasInteracted: boolean
}

interface OrderPreviewContextType {
  orderPreview: OrderPreviewData
  updateOrderPreview: (data: Partial<OrderPreviewData>) => void
  clearOrderPreview: () => void
}

const OrderPreviewContext = createContext<OrderPreviewContextType | undefined>(undefined)

export function OrderPreviewProvider({ children }: { children: ReactNode }) {
  const [orderPreview, setOrderPreview] = useState<OrderPreviewData>({
    symbol: '',
    side: null,
    entryPrice: null,
    takeProfitPrice: null,
    stopLossPrice: null,
    placeTakeProfit: false,
    placeStopLoss: false,
    hasInteracted: false,
  })

  const updateOrderPreview = useCallback((data: Partial<OrderPreviewData>) => {
    setOrderPreview(prev => ({ ...prev, ...data }))
  }, [])

  const clearOrderPreview = useCallback(() => {
    setOrderPreview({
      symbol: '',
      side: null,
      entryPrice: null,
      takeProfitPrice: null,
      stopLossPrice: null,
      placeTakeProfit: false,
      placeStopLoss: false,
      hasInteracted: false,
    })
  }, [])

  return (
    <OrderPreviewContext.Provider value={{ orderPreview, updateOrderPreview, clearOrderPreview }}>
      {children}
    </OrderPreviewContext.Provider>
  )
}

export function useOrderPreview() {
  const context = useContext(OrderPreviewContext)
  if (!context) {
    throw new Error('useOrderPreview must be used within OrderPreviewProvider')
  }
  return context
}