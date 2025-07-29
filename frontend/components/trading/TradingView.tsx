'use client'

import { useState, useEffect } from 'react'
import { ChartContainer } from './ChartContainer'
import { OrderBook } from './OrderBook'
import { OrderForm } from './OrderForm'
import { RecentTrades } from './RecentTrades'
import { OpenOrders } from './OpenOrders'
import { Positions } from './Positions'
import { MarketInfo } from './MarketInfo'
import { useMarket } from '@/contexts/MarketContext'
import { 
  ResizableLayout, 
  ResizablePanel, 
  ResizableHandle 
} from '@/components/layout/ResizableLayout'
import { useQuery } from '@tanstack/react-query'
import { tradingApi } from '@/lib/api'

export function TradingView() {
  const { selectedSymbol, selectedExchange } = useMarket()
  const [activeBottomTab, setActiveBottomTab] = useState<'balances' | 'orders' | 'history'>('orders')
  const [openOrderCount, setOpenOrderCount] = useState(0)

  // Fetch orders to get count
  const { data: orders = [] } = useQuery({
    queryKey: ['orders', selectedSymbol, selectedExchange],
    queryFn: () => tradingApi.getOrders(selectedSymbol, selectedExchange),
    refetchInterval: 5000,
  })

  // Update open order count
  useEffect(() => {
    const openOrders = orders.filter(order => 
      ['pending', 'open', 'partially_filled'].includes(order.status)
    )
    setOpenOrderCount(openOrders.length)
  }, [orders])

  return (
    <div className="h-full flex flex-col">
      {/* Market info bar */}
      <div className="h-12 border-b border-border-primary">
        <MarketInfo symbol={selectedSymbol} exchange={selectedExchange} />
      </div>

      {/* Main content with vertical split */}
      <ResizableLayout direction="vertical" autoSaveId="trading-vertical">
        {/* Top section - Chart and order book */}
        <ResizablePanel defaultSize={70} minSize={40}>
          <ResizableLayout direction="horizontal" autoSaveId="trading-top">
            {/* Chart */}
            <ResizablePanel defaultSize={70} minSize={40}>
              <ChartContainer symbol={selectedSymbol} />
            </ResizablePanel>
            
            <ResizableHandle />
            
            {/* Order book and trades */}
            <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
              <ResizableLayout direction="vertical" autoSaveId="trading-orderbook">
                {/* Order book */}
                <ResizablePanel defaultSize={60} minSize={30}>
                  <OrderBook symbol={selectedSymbol} />
                </ResizablePanel>
                
                <ResizableHandle direction="vertical" />
                
                {/* Recent trades */}
                <ResizablePanel defaultSize={40} minSize={20}>
                  <RecentTrades symbol={selectedSymbol} />
                </ResizablePanel>
              </ResizableLayout>
            </ResizablePanel>
          </ResizableLayout>
        </ResizablePanel>
        
        <ResizableHandle direction="vertical" />
        
        {/* Bottom section - Order form and tabs */}
        <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
          <ResizableLayout direction="horizontal" autoSaveId="trading-bottom">
            {/* Order form */}
            <ResizablePanel defaultSize={25} minSize={15} maxSize={40}>
              <div className="h-full border-r border-border-primary">
                <OrderForm symbol={selectedSymbol} exchange={selectedExchange} />
              </div>
            </ResizablePanel>
            
            <ResizableHandle />
            
            {/* Bottom tabs content */}
            <ResizablePanel defaultSize={75} minSize={50}>
              <div className="h-full flex flex-col">
                {/* Tab headers */}
                <div className="flex border-b border-border-primary">
                  <button
                    className={`px-4 py-2 text-xs font-medium ${
                      activeBottomTab === 'balances'
                        ? 'text-text-primary border-b-2 border-accent-primary'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                    onClick={() => setActiveBottomTab('balances')}
                  >
                    Balances
                  </button>
                  <button
                    className={`px-4 py-2 text-xs font-medium ${
                      activeBottomTab === 'orders'
                        ? 'text-text-primary border-b-2 border-accent-primary'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                    onClick={() => setActiveBottomTab('orders')}
                  >
                    Open Orders ({openOrderCount})
                  </button>
                  <button
                    className={`px-4 py-2 text-xs font-medium ${
                      activeBottomTab === 'history'
                        ? 'text-text-primary border-b-2 border-accent-primary'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                    onClick={() => setActiveBottomTab('history')}
                  >
                    Trade History
                  </button>
                </div>

                {/* Tab content */}
                <div className="flex-1 overflow-y-auto">
                  {activeBottomTab === 'balances' && <Positions exchange={selectedExchange} />}
                  {activeBottomTab === 'orders' && <OpenOrders symbol={selectedSymbol} exchange={selectedExchange} />}
                  {activeBottomTab === 'history' && (
                    <div className="p-4 text-center text-text-secondary text-sm">
                      Trade history coming soon
                    </div>
                  )}
                </div>
              </div>
            </ResizablePanel>
          </ResizableLayout>
        </ResizablePanel>
      </ResizableLayout>
    </div>
  )
}