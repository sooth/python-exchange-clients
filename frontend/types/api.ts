export interface Ticker {
  symbol: string
  base: string
  quote: string
  bid: number | string
  ask: number | string
  last: number | string
  high: number | string
  low: number | string
  volume: number | string
  quote_volume: number | string
  change: number | string
  change_percent: number | string
  timestamp: string
}

export interface OrderBookLevel {
  price: number
  amount: number
  total?: number
}

export interface OrderBook {
  symbol: string
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
  timestamp: string
  sequence?: number
}

export interface SymbolInfo {
  symbol: string
  base: string
  quote: string
  active: boolean
  type: string
  contract_size?: number
  tick_size: number
  lot_size: number
  min_notional?: number
  max_leverage?: number
  maker_fee: number
  taker_fee: number
}

export type OrderSide = 'buy' | 'sell'
export type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit' | 'take_profit' | 'take_profit_limit'
export type OrderStatus = 'pending' | 'open' | 'partially_filled' | 'filled' | 'cancelled' | 'rejected' | 'expired'
export type PositionSide = 'long' | 'short' | 'both'

export interface CreateOrderRequest {
  symbol: string
  side: OrderSide
  type: OrderType
  amount: number
  price?: number
  stop_price?: number
  time_in_force?: 'GTC' | 'IOC' | 'FOK' | 'GTX'
  post_only?: boolean
  reduce_only?: boolean
  client_order_id?: string
}

export interface OrderResponse {
  id: string
  client_order_id?: string
  symbol: string
  side: OrderSide
  type: OrderType
  status: OrderStatus
  price?: number | string
  average_price?: number | string
  amount: number | string
  filled: number | string
  remaining: number | string
  fee?: number | string
  fee_currency?: string
  timestamp: string
  updated?: string
  // Additional fields for TP/SL identification
  stop_price?: number | string
  trigger_price?: number | string
  reduce_only?: boolean
  post_only?: boolean
  time_in_force?: string
  raw_type?: string
}

export interface Position {
  symbol: string
  side: PositionSide
  size: number | string
  entry_price: number | string
  mark_price: number | string
  liquidation_price?: number | string
  unrealized_pnl: number | string
  realized_pnl: number | string
  margin: number | string
  leverage: number | string
  percentage: number | string
  timestamp: string
}

export interface Balance {
  currency: string
  free: number | string
  used: number | string
  total: number | string
}

export interface AccountInfo {
  id: string
  type: string
  balances: Record<string, Balance>
  total_value_usd?: number
  margin_level?: number
  leverage?: number
  timestamp: string
}