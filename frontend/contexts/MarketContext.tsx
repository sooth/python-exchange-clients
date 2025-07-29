'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

interface MarketContextType {
  selectedSymbol: string
  setSelectedSymbol: (symbol: string) => void
  selectedExchange: string
  setSelectedExchange: (exchange: string) => void
}

const MarketContext = createContext<MarketContextType | undefined>(undefined)

export function MarketProvider({ children }: { children: ReactNode }) {
  const [selectedSymbol, setSelectedSymbol] = useState(
    process.env.NEXT_PUBLIC_DEFAULT_SYMBOL || 'BTC-PERP'
  )
  const [selectedExchange, setSelectedExchange] = useState(
    process.env.NEXT_PUBLIC_DEFAULT_EXCHANGE || 'lmex'
  )

  return (
    <MarketContext.Provider 
      value={{ 
        selectedSymbol, 
        setSelectedSymbol, 
        selectedExchange, 
        setSelectedExchange 
      }}
    >
      {children}
    </MarketContext.Provider>
  )
}

export function useMarket() {
  const context = useContext(MarketContext)
  if (!context) {
    throw new Error('useMarket must be used within a MarketProvider')
  }
  return context
}