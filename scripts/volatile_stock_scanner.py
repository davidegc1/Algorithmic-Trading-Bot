"""
High Volatility Stock Scanner for NYSE/NASDAQ
Finds aggressive trading opportunities with high volatility and volume
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from typing import List, Dict
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VolatileStockScanner:
    """Scanner for high-volatility stocks on major exchanges"""
    
    def __init__(self):
        self.results = []
        # Load API keys from environment (if needed for future integrations)
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
    def get_stock_universe(self) -> List[str]:
        """
        Get a universe of potential stocks to scan
        Using popular volatile sectors and price ranges
        """
        # Common volatile tickers across key sectors
        volatile_universe = [
            # Biotech/Pharma (high volatility)
            'SAVA', 'TBPH', 'APLD', 'DRUG', 'ABOS', 'BDTX',
            'CGEM', 'DMAC', 'FBRX', 'IMMP', 'IRWD', 'MDGL', 'PRAX',
            
            # Small Cap Tech
            'IONQ', 'QUBT', 'RGTI', 'SOFI', 'UPST', 'HOOD', 'OPEN',
            'RKLB', 'ACHR', 'JOBY', 'LILM', 'EVTL', 'BIRD',
            
            # Crypto-related
            'MARA', 'RIOT', 'CLSK', 'CIFR', 'BITF', 'HUT', 'BTBT',
            'COIN', 'MSTR', 'SOS', 'CAN', 'BTCS',
            
            # EV/Battery
            'LCID', 'RIVN', 'WKHS', 'NKLA',
            
            # Cannabis
            'TLRY', 'CGC', 'SNDL', 'ACB', 'CRON', 'OGI',
            
            # High Beta Small Caps
            'GME', 'AMC', 'BBBY', 'KOSS', 'CLOV',
            'SKLZ', 'SPCE', 'PLTR', 'SNOW', 'RBLX',
            
            # Recent IPOs (typically volatile)
            'ARM', 'RDDT', 'KVUE', 'FBIN', 'CART', 'MNDY',
            
            # Other volatile names
            'PLUG', 'BLNK', 'CHPT', 'TSLA', 'NVDA', 'AMD', 'SMCI'
        ]
        
        return volatile_universe
    
    def calculate_metrics(self, ticker: str) -> Dict:
        """Calculate volatility and key metrics for a stock"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get historical data (90 days for better metrics)
            hist = stock.history(period='3mo')
            
            if hist.empty or len(hist) < 20:
                return None
            
            # Get current info
            info = stock.info
            
            # Calculate metrics
            current_price = hist['Close'].iloc[-1]
            
            # Historical volatility (annualized)
            returns = hist['Close'].pct_change().dropna()
            hist_volatility = returns.std() * np.sqrt(252) * 100
            
            # Average True Range (ATR)
            high_low = hist['High'] - hist['Low']
            high_close = np.abs(hist['High'] - hist['Close'].shift())
            low_close = np.abs(hist['Low'] - hist['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            atr_percent = (atr / current_price) * 100
            
            # Recent volatility (last 20 days)
            recent_returns = returns.tail(20)
            recent_volatility = recent_returns.std() * np.sqrt(252) * 100
            
            # Price movement metrics
            day_range = ((hist['High'].iloc[-1] - hist['Low'].iloc[-1]) / hist['Open'].iloc[-1]) * 100
            
            # Volume metrics
            avg_volume = hist['Volume'].tail(20).mean()
            current_volume = hist['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Price changes
            day_change = ((current_price - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1]) * 100
            week_change = ((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100 if len(hist) >= 5 else 0
            month_change = ((current_price - hist['Close'].iloc[-20]) / hist['Close'].iloc[-20]) * 100 if len(hist) >= 20 else 0
            
            # Beta (if available)
            beta = info.get('beta', None)
            
            # Market cap
            market_cap = info.get('marketCap', 0)
            market_cap_m = market_cap / 1_000_000 if market_cap else 0
            
            # Exchange
            exchange = info.get('exchange', 'Unknown')
            
            return {
                'ticker': ticker,
                'price': round(current_price, 2),
                'day_change_%': round(day_change, 2),
                'week_change_%': round(week_change, 2),
                'month_change_%': round(month_change, 2),
                'hist_volatility_%': round(hist_volatility, 2),
                'recent_volatility_%': round(recent_volatility, 2),
                'atr': round(atr, 2),
                'atr_%': round(atr_percent, 2),
                'day_range_%': round(day_range, 2),
                'volume': int(current_volume),
                'avg_volume': int(avg_volume),
                'volume_ratio': round(volume_ratio, 2),
                'beta': round(beta, 2) if beta else None,
                'market_cap_$M': round(market_cap_m, 1),
                'exchange': exchange
            }
            
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            return None
    
    def scan_stocks(self, tickers: List[str] = None, max_workers: int = 5) -> pd.DataFrame:
        """
        Scan stocks for volatility metrics
        """
        if tickers is None:
            tickers = self.get_stock_universe()
        
        print(f"Scanning {len(tickers)} stocks for volatility metrics...")
        print("This may take a few minutes...\n")
        
        results = []
        for i, ticker in enumerate(tickers, 1):
            print(f"Processing {i}/{len(tickers)}: {ticker}", end='\r')
            
            metrics = self.calculate_metrics(ticker)
            if metrics:
                results.append(metrics)
            
            # Rate limiting
            if i % 5 == 0:
                time.sleep(1)
        
        print("\n\nScan complete!")
        
        if not results:
            print("No results found")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        return df
    
    def filter_high_volatility(
        self,
        df: pd.DataFrame,
        min_price: float = 1.0,
        max_price: float = 10.0,
        min_volume: int = 1_000_000,
        min_volatility: float = 50.0,
        min_atr_percent: float = 3.0,
        max_market_cap_m: float = 2000.0
    ) -> pd.DataFrame:
        """
        Filter for high volatility stocks matching criteria
        """
        filtered = df[
            (df['price'] >= min_price) &
            (df['price'] <= max_price) &
            (df['avg_volume'] >= min_volume) &
            (df['hist_volatility_%'] >= min_volatility) &
            (df['atr_%'] >= min_atr_percent) &
            (df['market_cap_$M'] <= max_market_cap_m) &
            (df['market_cap_$M'] > 0)  # Exclude missing market cap
        ]
        
        # Sort by volatility score (combination of metrics)
        filtered['volatility_score'] = (
            filtered['hist_volatility_%'] * 0.4 +
            filtered['recent_volatility_%'] * 0.3 +
            filtered['atr_%'] * 20 * 0.3
        )
        
        filtered = filtered.sort_values('volatility_score', ascending=False)
        
        return filtered
    
    def get_top_movers_today(self, df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
        """Get stocks with biggest moves today"""
        return df.nlargest(top_n, 'day_change_%')[
            ['ticker', 'price', 'day_change_%', 'volume', 'volume_ratio', 
             'hist_volatility_%', 'atr_%', 'market_cap_$M']
        ]
    
    def get_volume_surge(self, df: pd.DataFrame, min_ratio: float = 2.0, top_n: int = 20) -> pd.DataFrame:
        """Get stocks with unusual volume"""
        surge = df[df['volume_ratio'] >= min_ratio].nlargest(top_n, 'volume_ratio')
        return surge[
            ['ticker', 'price', 'day_change_%', 'volume', 'volume_ratio',
             'hist_volatility_%', 'atr_%', 'market_cap_$M']
        ]


def main():
    """Run the scanner with default settings"""
    scanner = VolatileStockScanner()
    
    # Scan stocks
    df = scanner.scan_stocks()
    
    if df.empty:
        print("No data retrieved")
        return
    
    print(f"\n{'='*80}")
    print("VOLATILE STOCK SCANNER RESULTS")
    print(f"{'='*80}\n")
    
    # Filter for high volatility
    print("Filtering for high-volatility candidates...")
    filtered = scanner.filter_high_volatility(
        df,
        min_price=1.0,
        max_price=10.0,
        min_volume=1_000_000,
        min_volatility=50.0,  # 50%+ annualized volatility
        min_atr_percent=3.0,  # 3%+ daily ATR
        max_market_cap_m=2000.0  # Under $2B market cap
    )
    
    print(f"\nFound {len(filtered)} stocks matching criteria\n")
    
    # Top volatility candidates
    print(f"\n{'='*80}")
    print("TOP 20 HIGH VOLATILITY CANDIDATES")
    print(f"{'='*80}")
    top_volatile = filtered.head(20)[
        ['ticker', 'price', 'day_change_%', 'hist_volatility_%', 
         'atr_%', 'volume_ratio', 'market_cap_$M', 'exchange']
    ]
    print(top_volatile.to_string(index=False))
    
    # Today's top movers
    print(f"\n{'='*80}")
    print("TODAY'S TOP MOVERS (Biggest % Change)")
    print(f"{'='*80}")
    top_movers = scanner.get_top_movers_today(df, top_n=15)
    print(top_movers.to_string(index=False))
    
    # Volume surge
    print(f"\n{'='*80}")
    print("VOLUME SURGE ALERTS (2x+ Average Volume)")
    print(f"{'='*80}")
    volume_surge = scanner.get_volume_surge(df, min_ratio=2.0, top_n=15)
    if not volume_surge.empty:
        print(volume_surge.to_string(index=False))
    else:
        print("No stocks with 2x+ volume surge found")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save full results
    df.to_csv(f'/home/claude/volatile_stocks_full_{timestamp}.csv', index=False)
    print(f"\n\nFull results saved to: volatile_stocks_full_{timestamp}.csv")
    
    # Save filtered results
    if not filtered.empty:
        filtered.to_csv(f'/home/claude/volatile_stocks_filtered_{timestamp}.csv', index=False)
        print(f"Filtered results saved to: volatile_stocks_filtered_{timestamp}.csv")
    
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Total stocks scanned: {len(df)}")
    print(f"High volatility candidates: {len(filtered)}")
    print(f"Average volatility: {df['hist_volatility_%'].mean():.1f}%")
    print(f"Highest volatility: {df['hist_volatility_%'].max():.1f}% ({df.loc[df['hist_volatility_%'].idxmax(), 'ticker']})")
    print(f"Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
    

if __name__ == "__main__":
    main()
