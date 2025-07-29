'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { MarketProvider } from '@/contexts/MarketContext'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 1000, // 5 seconds
            refetchInterval: 10 * 1000, // 10 seconds
          },
        },
      })
  )

  useEffect(() => {
    // Clear all caches on mount to prevent stale data
    queryClient.clear()
  }, [queryClient])

  return (
    <QueryClientProvider client={queryClient}>
      <MarketProvider>
        {children}
      </MarketProvider>
    </QueryClientProvider>
  )
}