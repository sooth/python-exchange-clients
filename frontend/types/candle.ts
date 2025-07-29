// API response format
export interface CandleResponse {
  timestamp: string  // ISO datetime string from backend
  open: string | number  // Backend returns strings
  high: string | number  // Backend returns strings
  low: string | number   // Backend returns strings
  close: string | number  // Backend returns strings
  volume: string | number // Backend returns strings
}

// Chart format (for lightweight-charts)
export interface ChartCandle {
  time: number  // Unix timestamp in seconds
  open: number
  high: number
  low: number
  close: number
  volume?: number
}