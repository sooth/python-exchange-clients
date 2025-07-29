import { useEffect, useCallback, useState } from 'react'
import { getWebSocketClient } from '@/lib/websocket'
import type { WSMessage } from '@/lib/websocket'

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const wsClient = getWebSocketClient()

  useEffect(() => {
    const handleConnected = () => setIsConnected(true)
    const handleDisconnected = () => setIsConnected(false)

    wsClient.addEventListener('connected', handleConnected)
    wsClient.addEventListener('disconnected', handleDisconnected)

    // Connect if not already connected
    wsClient.connect()

    return () => {
      wsClient.removeEventListener('connected', handleConnected)
      wsClient.removeEventListener('disconnected', handleDisconnected)
    }
  }, [wsClient])

  const subscribe = useCallback(
    (channel: string, symbols: string[]) => {
      wsClient.subscribe(channel, symbols)
    },
    [wsClient]
  )

  const unsubscribe = useCallback(
    (channel: string, symbols: string[]) => {
      wsClient.unsubscribe(channel, symbols)
    },
    [wsClient]
  )

  return {
    isConnected,
    subscribe,
    unsubscribe,
    wsClient,
  }
}

export function useWebSocketSubscription<T = unknown>(
  channel: string,
  symbols: string[],
  onData: (symbol: string, data: T) => void
) {
  const { subscribe, unsubscribe, wsClient } = useWebSocket()

  useEffect(() => {
    if (symbols.length === 0) return

    const handleData = (event: CustomEvent) => {
      const { symbol, data } = event.detail
      if (symbols.includes(symbol)) {
        onData(symbol, data)
      }
    }

    wsClient.addEventListener(channel, handleData as EventListener)
    subscribe(channel, symbols)

    return () => {
      wsClient.removeEventListener(channel, handleData as EventListener)
      unsubscribe(channel, symbols)
    }
  }, [channel, symbols, onData, subscribe, unsubscribe, wsClient])
}