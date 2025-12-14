"""
Alpaca Trading Integration Helper
Use scanner results to execute trades via Alpaca API
"""

import os
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class AlpacaTrader:
    """Helper class for executing trades based on scanner results"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing Alpaca API credentials in .env file")
        
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret
        }
    
    def get_account(self) -> Dict:
        """Get account information"""
        url = f"{self.base_url}/v2/account"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_buying_power(self) -> float:
        """Get available buying power"""
        account = self.get_account()
        return float(account.get('buying_power', 0))
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        url = f"{self.base_url}/v2/positions"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def check_if_tradeable(self, symbol: str) -> bool:
        """Check if a symbol is tradeable on Alpaca"""
        url = f"{self.base_url}/v2/assets/{symbol}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            asset = response.json()
            return asset.get('tradable', False) and asset.get('status') == 'active'
        return False
    
    def filter_tradeable_stocks(self, scanner_results: pd.DataFrame) -> pd.DataFrame:
        """Filter scanner results to only tradeable stocks on Alpaca"""
        print("Checking which stocks are tradeable on Alpaca...\n")
        
        tradeable = []
        for _, row in scanner_results.iterrows():
            symbol = row['ticker']
            if self.check_if_tradeable(symbol):
                tradeable.append(row)
                print(f"✓ {symbol}")
            else:
                print(f"✗ {symbol} (not tradeable)")
        
        return pd.DataFrame(tradeable) if tradeable else pd.DataFrame()
    
    def place_order(
        self,
        symbol: str,
        qty: Optional[int] = None,
        notional: Optional[float] = None,
        side: str = 'buy',
        order_type: str = 'market',
        time_in_force: str = 'day'
    ) -> Dict:
        """
        Place an order
        
        Args:
            symbol: Stock ticker
            qty: Number of shares (use qty OR notional, not both)
            notional: Dollar amount to invest (use qty OR notional, not both)
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
        """
        url = f"{self.base_url}/v2/orders"
        
        order_data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'time_in_force': time_in_force
        }
        
        if qty:
            order_data['qty'] = qty
        elif notional:
            order_data['notional'] = notional
        else:
            raise ValueError("Must specify either qty or notional")
        
        response = requests.post(url, json=order_data, headers=self.headers)
        return response.json()
    
    def create_watchlist(self, name: str, symbols: List[str]) -> Dict:
        """Create a watchlist in Alpaca"""
        url = f"{self.base_url}/v2/watchlists"
        
        data = {
            'name': name,
            'symbols': symbols
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()
    
    def get_bars(self, symbol: str, timeframe: str = '1Day', limit: int = 100) -> pd.DataFrame:
        """Get historical bars for a symbol"""
        url = f"{self.base_url}/v2/stocks/{symbol}/bars"
        
        params = {
            'timeframe': timeframe,
            'limit': limit
        }
        
        response = requests.get(url, params=params, headers=self.headers)
        data = response.json()
        
        if 'bars' in data:
            return pd.DataFrame(data['bars'])
        return pd.DataFrame()


def example_workflow():
    """Example workflow: Scanner -> Filter -> Trade"""
    
    print("="*80)
    print("ALPACA TRADING INTEGRATION EXAMPLE")
    print("="*80 + "\n")
    
    # Initialize trader
    trader = AlpacaTrader()
    
    # Check account
    account = trader.get_account()
    print(f"Account Status: {account.get('status')}")
    print(f"Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
    print(f"Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}\n")
    
    # Example: Load scanner results
    print("Load your scanner results CSV file first, then use this script to:")
    print("1. Filter for tradeable stocks on Alpaca")
    print("2. Create watchlists")
    print("3. Execute trades based on your strategy")
    print("\nExample:")
    print("  df = pd.read_csv('high_risk_plays_20241212.csv')")
    print("  tradeable = trader.filter_tradeable_stocks(df)")
    print("  # Review and execute trades manually or programmatically")


if __name__ == "__main__":
    example_workflow()
