'use client'

import { useMarket } from '@/contexts/MarketContext'

export function DebugInfo() {
  const { selectedSymbol, selectedExchange } = useMarket()
  
  return (
    <div className="fixed bottom-4 right-4 bg-black/80 text-white p-2 rounded text-xs font-mono z-50">
      <div>Exchange: {selectedExchange}</div>
      <div>Symbol: {selectedSymbol}</div>
      <div>Env Exchange: {process.env.NEXT_PUBLIC_DEFAULT_EXCHANGE}</div>
      <div>Env Symbol: {process.env.NEXT_PUBLIC_DEFAULT_SYMBOL}</div>
    </div>
  )
}