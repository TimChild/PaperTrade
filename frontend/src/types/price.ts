/**
 * Price-related types for market data
 * These types match the backend PricePoint DTO structure
 */

/**
 * Ticker object matching backend structure
 */
export interface Ticker {
  symbol: string
}

/**
 * Money object matching backend structure
 */
export interface Money {
  amount: number
  currency: string
}

/**
 * PricePoint represents a single price observation for a ticker
 * Matches backend PricePoint DTO from Task 018
 */
export interface PricePoint {
  ticker: Ticker
  price: Money
  timestamp: string // ISO 8601 datetime string
  source: 'alpha_vantage' | 'cache' | 'database'
  interval: 'real-time' | '1day' | '1hour' | '5min' | '1min'
  // Optional OHLCV data
  open?: Money
  high?: Money
  low?: Money
  close?: Money
  volume?: number
}
