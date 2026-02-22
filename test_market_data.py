#!/usr/bin/env python3
"""
Test market data with NSE fallback
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.market_data import MarketDataFetcher
import asyncio

async def test_market_data():
    print("🔍 Testing Market Data with NSE Fallback...")
    
    fetcher = MarketDataFetcher()
    
    # Test stock data
    print("\n📈 Testing Stock OHLCV Data:")
    reliance_data = await fetcher.get_ohlcv("RELIANCE")
    print(f"RELIANCE Data:\n{reliance_data}")
    
    tcs_data = await fetcher.get_ohlcv("TCS")
    print(f"TCS Data:\n{tcs_data}")
    
    # Test index data
    print("\n📊 Testing Index Summary:")
    indices = await fetcher.get_index_summary()
    print(f"Indices: {indices}")

if __name__ == "__main__":
    asyncio.run(test_market_data())
