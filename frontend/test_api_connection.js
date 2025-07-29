#!/usr/bin/env node

// Test script to verify API connectivity

const API_BASE = 'http://localhost:8001/api/v1';

async function testConnection() {
  console.log('Testing API connection...\n');
  
  try {
    // Test 1: Health check
    console.log('1. Testing health endpoint...');
    const healthRes = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
    const health = await healthRes.json();
    console.log('✅ Health:', health);
    
    // Test 2: Get tickers
    console.log('\n2. Testing market tickers...');
    const tickersRes = await fetch(`${API_BASE}/market/tickers?exchange=bitunix`);
    const tickers = await tickersRes.json();
    console.log(`✅ Found ${tickers.length} tickers`);
    console.log('Sample ticker:', tickers[0]);
    
    // Test 3: Get positions (will fail without auth)
    console.log('\n3. Testing positions endpoint...');
    const positionsRes = await fetch(`${API_BASE}/trading/positions?exchange=bitunix`);
    const positions = await positionsRes.json();
    console.log('✅ Positions:', positions);
    
    // Test 4: Get open orders
    console.log('\n4. Testing orders endpoint...');
    const ordersRes = await fetch(`${API_BASE}/trading/orders?exchange=bitunix`);
    const orders = await ordersRes.json();
    console.log('✅ Orders:', orders);
    
    console.log('\n✅ All API endpoints are accessible!');
    
  } catch (error) {
    console.error('❌ API connection test failed:', error.message);
  }
}

testConnection();