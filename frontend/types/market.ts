export interface Candle {
  timestamp: number  // Unix timestamp in seconds
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Trade {
  id?: string
  symbol: string
  price: number
  amount: number
  side: 'buy' | 'sell'
  timestamp: number  // Unix timestamp in milliseconds
}

export interface OrderBookLevel {
  price: number
  amount: number
  total?: number
}