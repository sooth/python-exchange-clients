'use client'

import { useEffect } from 'react'
import { useMarket } from '@/contexts/MarketContext'

export function ForceDefaults() {
  const { selectedExchange, selectedSymbol, setSelectedExchange, setSelectedSymbol } = useMarket()
  
  useEffect(() => {
    // Force LMEX defaults if still using old values
    if (selectedExchange === 'bitunix' || !selectedExchange) {
      console.log('Forcing exchange to lmex from:', selectedExchange)
      setSelectedExchange('lmex')
    }
    
    if (selectedSymbol === 'BTCUSDT' || !selectedSymbol) {
      console.log('Forcing symbol to BTC-PERP from:', selectedSymbol)
      setSelectedSymbol('BTC-PERP')
    }
  }, [selectedExchange, selectedSymbol, setSelectedExchange, setSelectedSymbol])
  
  return null
}