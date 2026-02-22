#!/usr/bin/env python3
"""
Test NSE data fetching (OpenChart)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.nse_data import NSEDataFetcher

def test_nse():
    print("🔍 Testing NSE (OpenChart)...")
    fetcher = NSEDataFetcher()

    # Index data (pass display name + legacy ticker)
    print("\n📊 Index data:")
    for name, ticker in [("NIFTY 50", "^NSEI"), ("NIFTY BANK", "^NSEBANK")]:
        data = fetcher.get_index_data(name, ticker)
        print(f"  {name}: {data}")

    # Stock OHLCV
    print("\n📈 Stock OHLCV:")
    for symbol in ["RELIANCE", "TCS"]:
        df = fetcher.get_stock_data(symbol)
        print(f"  {symbol}: {len(df)} rows")
        if not df.empty:
            print(df.tail(2).to_string())

if __name__ == "__main__":
    test_nse()
