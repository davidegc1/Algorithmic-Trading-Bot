"""
Real-time Watchlist Monitor
Continuously monitor a watchlist of high-volatility stocks
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WatchlistMonitor:
    """Monitor specific tickers in real-time"""
    
    def __init__(self, watchlist: List[str], alert_threshold: float = 5.0):
        self.watchlist = [t.upper() for t in watchlist]
        self.alert_threshold = alert_threshold
        self.previous_prices = {}
        # Load API keys from environment (for future integrations)
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
    def get_snapshot(self, ticker: str) -> Dict:
        """Get current snapshot of ticker"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get today's data
            today = stock.history(period='1d', interval='1m')
            
            if today.empty:
                return None
            
            current_price = today['Close'].iloc[-1]
            open_price = today['Open'].iloc[0]
            high = today['High'].max()
            low = today['Low'].min()
            volume = today['Volume'].sum()
            
            # Calculate metrics
            day_change = ((current_price - open_price) / open_price) * 100
            day_range = ((high - low) / open_price) * 100
            
            # Recent minute volatility
            minute_returns = today['Close'].pct_change().dropna()
            minute_vol = minute_returns.std() * 100 if len(minute_returns) > 0 else 0
            
            # Last 5 minute trend
            if len(today) >= 5:
                recent_change = ((current_price - today['Close'].iloc[-6]) / today['Close'].iloc[-6]) * 100
            else:
                recent_change = 0
            
            return {
                'ticker': ticker,
                'price': round(current_price, 2),
                'day_change_%': round(day_change, 2),
                'last_5min_%': round(recent_change, 2),
                'day_range_%': round(day_range, 2),
                'volume': int(volume),
                'high': round(high, 2),
                'low': round(low, 2),
                'volatility': round(minute_vol, 2),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            
        except Exception as e:
            return None
    
    def monitor_once(self) -> pd.DataFrame:
        """Get one snapshot of all watchlist tickers"""
        results = []
        
        for ticker in self.watchlist:
            snapshot = self.get_snapshot(ticker)
            if snapshot:
                results.append(snapshot)
                
                # Check for alerts
                price = snapshot['price']
                day_change = snapshot['day_change_%']
                
                # Price movement alert
                if abs(day_change) >= self.alert_threshold:
                    direction = "UP" if day_change > 0 else "DOWN"
                    print(f"\n🚨 ALERT: {ticker} {direction} {abs(day_change):.2f}% to ${price}")
                
                # Track price changes between refreshes
                if ticker in self.previous_prices:
                    prev_price = self.previous_prices[ticker]
                    quick_change = ((price - prev_price) / prev_price) * 100
                    
                    if abs(quick_change) >= 2.0:  # 2% move since last check
                        print(f"⚡ {ticker}: {quick_change:+.2f}% in last minute (${prev_price:.2f} → ${price:.2f})")
                
                self.previous_prices[ticker] = price
            
            time.sleep(0.5)  # Rate limiting
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    
    def monitor_continuous(self, refresh_seconds: int = 60, duration_minutes: int = 60):
        """Monitor watchlist continuously"""
        
        print(f"\n{'='*100}")
        print(f"MONITORING {len(self.watchlist)} STOCKS")
        print(f"Alert threshold: {self.alert_threshold}%")
        print(f"Refresh rate: {refresh_seconds}s")
        print(f"Duration: {duration_minutes} minutes")
        print(f"{'='*100}\n")
        print(f"Watchlist: {', '.join(self.watchlist)}\n")
        
        start_time = time.time()
        iterations = 0
        
        try:
            while True:
                elapsed = (time.time() - start_time) / 60
                if elapsed >= duration_minutes:
                    print(f"\nMonitoring complete ({duration_minutes} minutes elapsed)")
                    break
                
                iterations += 1
                current_time = datetime.now().strftime('%H:%M:%S')
                
                print(f"\n{'='*100}")
                print(f"UPDATE #{iterations} at {current_time} (Elapsed: {elapsed:.1f} min)")
                print(f"{'='*100}")
                
                df = self.monitor_once()
                
                if not df.empty:
                    # Sort by biggest movers
                    df_sorted = df.sort_values('day_change_%', key=abs, ascending=False)
                    
                    display_cols = ['ticker', 'price', 'day_change_%', 'last_5min_%', 
                                  'day_range_%', 'volume', 'volatility']
                    print(df_sorted[display_cols].to_string(index=False))
                    
                    # Show top movers
                    print(f"\n📈 Biggest Gainer: {df_sorted.iloc[0]['ticker']} "
                          f"({df_sorted.iloc[0]['day_change_%']:+.2f}%)")
                    
                    losers = df_sorted[df_sorted['day_change_%'] < 0]
                    if not losers.empty:
                        print(f"📉 Biggest Loser: {losers.iloc[0]['ticker']} "
                              f"({losers.iloc[0]['day_change_%']:+.2f}%)")
                else:
                    print("No data retrieved")
                
                # Wait before next refresh
                print(f"\nNext update in {refresh_seconds} seconds...")
                time.sleep(refresh_seconds)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        
        print(f"\nTotal updates: {iterations}")


def main():
    """Run watchlist monitor"""
    
    print("\n" + "="*100)
    print("REAL-TIME WATCHLIST MONITOR")
    print("="*100)
    
    # Example watchlists
    print("\nPre-configured watchlists:")
    print("1. Crypto Stocks (MARA, RIOT, COIN, MSTR, CLSK)")
    print("2. Biotech High Vol (SAVA, TBPH, IRWD, PRAX, BLUE)")
    print("3. Small Cap Tech (IONQ, SOFI, HOOD, RKLB, PLTR)")
    print("4. Meme Stocks (GME, AMC, BBBY, CLOV, EXPR)")
    print("5. Custom watchlist")
    
    choice = input("\nSelect watchlist (1-5): ").strip()
    
    watchlists = {
        '1': ['MARA', 'RIOT', 'COIN', 'MSTR', 'CLSK', 'CIFR', 'BITF'],
        '2': ['SAVA', 'TBPH', 'IRWD', 'PRAX', 'BLUE', 'SRPT', 'BMRN'],
        '3': ['IONQ', 'SOFI', 'HOOD', 'RKLB', 'PLTR', 'SNOW', 'UPST'],
        '4': ['GME', 'AMC', 'BBBY', 'CLOV', 'EXPR', 'KOSS']
    }
    
    if choice in watchlists:
        watchlist = watchlists[choice]
    elif choice == '5':
        tickers_input = input("Enter tickers (comma-separated): ").strip()
        watchlist = [t.strip().upper() for t in tickers_input.split(',')]
    else:
        print("Invalid choice, using crypto stocks")
        watchlist = watchlists['1']
    
    # Get parameters
    try:
        alert = float(input(f"Alert threshold % (default 5): ").strip() or "5")
        refresh = int(input(f"Refresh interval seconds (default 60): ").strip() or "60")
        duration = int(input(f"Duration minutes (default 60): ").strip() or "60")
    except:
        alert, refresh, duration = 5.0, 60, 60
    
    # Start monitoring
    monitor = WatchlistMonitor(watchlist, alert_threshold=alert)
    monitor.monitor_continuous(refresh_seconds=refresh, duration_minutes=duration)


if __name__ == "__main__":
    main()
