"""
NSE Direct API Data Fetcher
Fallback when yfinance fails
"""

import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger("NSEData")

class NSEDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def get_index_data(self, index_symbol: str) -> Dict[str, Any]:
        """Get index data from NSE"""
        try:
            if index_symbol == "^NSEI":
                url = "https://www.nseindia.com/api/index-equities?index=NIFTY%2050"
            elif index_symbol == "^NSEBANK":
                url = "https://www.nseindia.com/api/index-equities?index=NIFTY%20BANK"
            else:
                return {"price": None, "change_pct": None, "trend": "—"}
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    index_data = data['data'][0]
                    current_price = index_data.get('lastPrice', 0)
                    previous_price = index_data.get('previousClose', 0)
                    
                    if previous_price > 0:
                        change_pct = ((current_price - previous_price) / previous_price) * 100
                        return {
                            "price": round(current_price, 2),
                            "change_pct": round(change_pct, 2),
                            "trend": "▲" if change_pct >= 0 else "▼"
                        }
            
            return {"price": None, "change_pct": None, "trend": "—"}
            
        except Exception as e:
            logger.error(f"NSE index data failed for {index_symbol}: {e}")
            return {"price": None, "change_pct": None, "trend": "—"}
    
    def get_stock_data(self, symbol: str) -> pd.DataFrame:
        """Get stock data from NSE"""
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'priceInfo' in data and 'data' in data:
                    price_info = data['priceInfo']
                    
                    # Create minimal DataFrame with recent data
                    current_price = price_info.get('lastPrice', 0)
                    previous_price = price_info.get('previousClose', 0)
                    volume = price_info.get('totalTradedVolume', 0)
                    
                    # Create synthetic OHLCV data
                    df = pd.DataFrame({
                        'Open': [previous_price],
                        'High': [max(current_price, previous_price)],
                        'Low': [min(current_price, previous_price)],
                        'Close': [current_price],
                        'Volume': [volume]
                    }, index=[pd.Timestamp.now()])
                    
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"NSE stock data failed for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_stock_price_info(self, symbol: str) -> Dict[str, Any]:
        """Get basic stock price info"""
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'priceInfo' in data:
                    price_info = data['priceInfo']
                    return {
                        'current_price': price_info.get('lastPrice', 0),
                        'previous_close': price_info.get('previousClose', 0),
                        'change': price_info.get('change', 0),
                        'pchange': price_info.get('pChange', 0),
                        'volume': price_info.get('totalTradedVolume', 0),
                        'symbol': symbol
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"NSE price info failed for {symbol}: {e}")
            return {}
