"""
Dynamic Stock Universe Builder
Automatically discovers and filters stocks from the entire market based on volatility criteria
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from typing import List, Dict, Optional
import os
import csv
from dotenv import load_dotenv

load_dotenv()


class UniverseBuilder:
    """Build a dynamic stock universe by screening the entire market"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    def get_all_nasdaq_tickers(self) -> List[str]:
        """
        Get all NASDAQ-listed tickers
        Source: NASDAQ FTP site (public data)
        """
        print("Fetching all NASDAQ tickers...")
        
        try:
            # NASDAQ provides free list of all traded securities
            url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
            
            # Download using pandas
            df = pd.read_csv(url, sep='|')
            
            # Filter out the last row (file creation timestamp)
            df = df[df['Symbol'] != 'File Creation Time']
            
            # Get symbols - convert to string and handle NaN
            tickers = df['Symbol'].dropna().astype(str).tolist()
            
            # Exclude test symbols and invalid entries
            tickers = [
                t for t in tickers 
                if isinstance(t, str) and 
                not t.endswith(('.TEST', '.U', '.W', '.R')) and
                not t.lower() in ('nan', 'none', '')
            ]
            
            print(f"✓ Found {len(tickers)} NASDAQ tickers")
            return tickers
            
        except Exception as e:
            print(f"Error fetching NASDAQ tickers: {e}")
            return []
    
    def get_all_nyse_tickers(self) -> List[str]:
        """
        Get all NYSE-listed tickers
        Source: NASDAQ FTP site (includes NYSE data)
        """
        print("Fetching all NYSE tickers...")
        
        try:
            # NYSE data also available from NASDAQ
            url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
            
            df = pd.read_csv(url, sep='|')
            df = df[df['ACT Symbol'] != 'File Creation Time']
            
            # Filter for NYSE only (exchange code 'N')
            nyse_df = df[df['Exchange'] == 'N']
            
            tickers = nyse_df['ACT Symbol'].tolist()
            tickers = [t for t in tickers if not t.endswith(('.TEST', '.U', '.W', '.R'))]
            
            print(f"✓ Found {len(tickers)} NYSE tickers")
            return tickers
            
        except Exception as e:
            print(f"Error fetching NYSE tickers: {e}")
            return []
    
    def get_sp500_tickers(self) -> List[str]:
        """Get S&P 500 tickers from Wikipedia"""
        print("Fetching S&P 500 tickers...")
        
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_table = tables[0]
            tickers = sp500_table['Symbol'].tolist()
            
            # Clean up tickers (Wikipedia uses class A/B suffixes)
            tickers = [t.replace('.', '-') for t in tickers]
            
            print(f"✓ Found {len(tickers)} S&P 500 tickers")
            return tickers
            
        except Exception as e:
            print(f"Error fetching S&P 500 tickers: {e}")
            return []
    
    def get_russell2000_tickers(self) -> List[str]:
        """
        Get Russell 2000 tickers (small caps - typically more volatile)
        Note: This requires scraping or a paid data source
        """
        print("Russell 2000 requires paid data source - skipping")
        return []
    
    def get_all_market_tickers(
        self,
        include_nasdaq: bool = True,
        include_nyse: bool = True,
        include_sp500: bool = False
    ) -> List[str]:
        """
        Get comprehensive list of all tradeable stocks
        
        Returns ~8,000-10,000 tickers from major exchanges
        """
        print("\n" + "="*80)
        print("BUILDING COMPREHENSIVE MARKET UNIVERSE")
        print("="*80 + "\n")
        
        all_tickers = []
        
        if include_nasdaq:
            all_tickers.extend(self.get_all_nasdaq_tickers())
        
        if include_nyse:
            all_tickers.extend(self.get_all_nyse_tickers())
        
        if include_sp500:
            all_tickers.extend(self.get_sp500_tickers())
        
        # Remove duplicates
        all_tickers = list(set(all_tickers))
        
        # Filter out ETFs, funds, warrants, units, preferred stocks
        print("\nFiltering out non-stocks...")
        filtered = []
        for ticker in all_tickers:
            # Skip preferred stocks (contain $)
            if '$' in ticker:
                continue
            # Skip common ETF/fund identifiers
            if any(x in ticker for x in ['^', '/', '.', '-WT', '-WS', '-U', '-R']):
                continue
            # Skip if ticker is too long (usually warrants/units)
            if len(ticker) > 5:
                continue
            # Skip if not alphanumeric
            if not ticker.replace('-', '').isalnum():
                continue
            filtered.append(ticker)
        
        print(f"✓ Total unique stock tickers: {len(filtered)}\n")
        return filtered
    
    def quick_screen_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Quick screening of a single ticker
        Returns basic metrics or None if doesn't meet minimum criteria
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get quick info
            info = stock.info
            
            # Fast filters - skip if doesn't meet basic criteria
            price = info.get('currentPrice') or info.get('previousClose')
            if not price or price < 0.50 or price > 50:  # Outside target range
                return None
            
            volume = info.get('averageVolume') or info.get('volume')
            if not volume or volume < 500_000:  # Too illiquid
                return None
            
            market_cap = info.get('marketCap')
            if not market_cap or market_cap > 5_000_000_000:  # Too large (>$5B)
                return None
            
            # Get minimal historical data for volatility
            hist = stock.history(period='3mo')
            
            if hist.empty or len(hist) < 10:
                return None
            
            # Calculate multi-timeframe volatility
            returns = hist['Close'].pct_change().dropna()
            if len(returns) < 5:
                return None
            
            # Monthly volatility (most relevant for screening)
            if len(returns) >= 20:
                monthly_returns = returns.tail(20)
                volatility = monthly_returns.std() * np.sqrt(252) * 100
            else:
                volatility = returns.std() * np.sqrt(252) * 100
            
            # Must have minimum volatility
            if volatility < 50:  # Less than 50% annualized
                return None
            
            return {
                'ticker': ticker,
                'price': round(price, 2),
                'volume': int(volume),
                'market_cap': market_cap,
                'volatility': round(volatility, 2),
                'exchange': info.get('exchange', 'Unknown')
            }
            
        except Exception as e:
            return None
    
    def batch_screen_universe(
        self,
        tickers: List[str],
        batch_size: int = 50,
        max_tickers: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Screen a large universe of tickers in batches
        
        Args:
            tickers: List of ticker symbols to screen
            batch_size: Number of tickers to process before pausing
            max_tickers: Maximum number to process (for testing)
        """
        if max_tickers:
            tickers = tickers[:max_tickers]
        
        print(f"\n{'='*80}")
        print(f"SCREENING {len(tickers)} TICKERS")
        print(f"This will take approximately {len(tickers) // 60} minutes")
        print(f"{'='*80}\n")
        
        results = []
        start_time = time.time()
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Screening {ticker}...", end='\r')
            
            metrics = self.quick_screen_ticker(ticker)
            if metrics:
                results.append(metrics)
                print(f"[{i}/{len(tickers)}] ✓ {ticker} - {metrics['volatility']:.1f}% vol", end='\r')
            
            # Rate limiting - pause after each batch
            if i % batch_size == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = len(tickers) - i
                eta = remaining / rate / 60
                
                print(f"\n[Batch {i//batch_size}] Processed {i} tickers | Found {len(results)} candidates | ETA: {eta:.1f} min")
                time.sleep(2)  # Pause between batches
        
        elapsed_total = (time.time() - start_time) / 60
        print(f"\n\n✓ Screening complete in {elapsed_total:.1f} minutes")
        print(f"✓ Found {len(results)} high-volatility candidates")
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    
    def rank_and_filter_universe(
        self,
        df: pd.DataFrame,
        min_volatility: float = 50,
        min_volume: int = 1_000_000,
        max_market_cap: float = 10_000_000_000,
        top_n: int = 200
    ) -> pd.DataFrame:
        """
        Apply final filters and rank the discovered universe
        """
        print(f"\n{'='*80}")
        print("APPLYING FINAL FILTERS")
        print(f"{'='*80}\n")
        
        # Apply filters
        filtered = df[
            (df['volatility'] >= min_volatility) &
            (df['volume'] >= min_volume) &
            (df['market_cap'] <= max_market_cap)
        ].copy()
        
        print(f"After filters: {len(filtered)} stocks")
        
        # Sort by volatility
        filtered = filtered.sort_values('volatility', ascending=False)
        
        # Take top N
        filtered = filtered.head(top_n)
        
        print(f"Top {min(top_n, len(filtered))} selected for universe")
        
        return filtered
    
    def save_universe(self, df: pd.DataFrame, filename: str = None):
        """Save the universe to a file in organized directory structure"""
        
        # Create timestamp for this universe
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create main universes directory if it doesn't exist
        base_dir = 'universes'
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            print(f"✓ Created main directory: {base_dir}/")
        
        # Create subdirectory for this specific universe
        universe_dir = os.path.join(base_dir, f'universe_{timestamp}')
        os.makedirs(universe_dir, exist_ok=True)
        print(f"✓ Created universe directory: {universe_dir}/")
        
        # WORKAROUND: Use native Python CSV writing instead of pandas.to_csv()
        csv_file = os.path.join(universe_dir, f'universe_data.csv')
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(df.columns.tolist())
                # Write data
                for _, row in df.iterrows():
                    writer.writerow(row.tolist())
            print(f"✓ Saved data: {csv_file}")
        except Exception as e:
            print(f"❌ Error saving CSV: {e}")
            return None
        
        # Save ticker list
        ticker_file = os.path.join(universe_dir, f'universe_tickers.txt')
        with open(ticker_file, 'w') as f:
            f.write('\n'.join(df['ticker'].tolist()))
        print(f"✓ Saved tickers: {ticker_file}")
        
        # Save Python module
        python_file = os.path.join(universe_dir, f'universe.py')
        self.generate_python_universe_to_file(df, python_file, timestamp)
        print(f"✓ Saved Python module: {python_file}")
        
        # Save metadata/stats
        metadata_file = os.path.join(universe_dir, 'metadata.json')
        metadata = {
            'created': timestamp,
            'total_stocks': len(df),
            'avg_volatility': float(df['volatility'].mean()),
            'max_volatility': float(df['volatility'].max()),
            'min_volatility': float(df['volatility'].min()),
            'avg_volume': int(df['volume'].mean()),
            'avg_market_cap': float(df['market_cap'].mean()),
            'price_range': {
                'min': float(df['price'].min()),
                'max': float(df['price'].max())
            },
            'top_10_tickers': df.nlargest(10, 'volatility')['ticker'].tolist()
        }
        
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Saved metadata: {metadata_file}")
        
        # Create README for this universe
        readme_file = os.path.join(universe_dir, 'README.md')
        self.create_universe_readme(df, readme_file, timestamp)
        print(f"✓ Saved README: {readme_file}")
        
        # Also save a copy of universe.py to main directory for easy import
        main_universe_file = 'custom_universe.py'
        self.generate_python_universe_to_file(df, main_universe_file, timestamp)
        print(f"✓ Saved main universe file: {main_universe_file}")
        
        print(f"\n{'='*80}")
        print(f"Universe saved to: {universe_dir}/")
        print(f"{'='*80}")
        
        return universe_dir
    
    def generate_python_universe(self, df: pd.DataFrame, filename: str = 'custom_universe.py'):
        """
        Generate a Python file with the universe as a list
        Can be imported directly into scanners
        """
        self.generate_python_universe_to_file(df, filename, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return filename
    
    def generate_python_universe_to_file(self, df: pd.DataFrame, filepath: str, timestamp: str):
        """Helper to generate Python universe file to specific path"""
        tickers = df['ticker'].tolist()
        
        code = f'''"""
Auto-generated Stock Universe
Created: {timestamp}
Total stocks: {len(tickers)}
Criteria: High volatility, sufficient liquidity
"""

CUSTOM_UNIVERSE = {tickers}

# Statistics
UNIVERSE_STATS = {{
    'total_stocks': {len(df)},
    'avg_volatility': {df['volatility'].mean():.2f},
    'avg_volume': {int(df['volume'].mean())},
    'price_range': (${df['price'].min():.2f}, ${df['price'].max():.2f}),
    'generated': '{timestamp}'
}}

if __name__ == "__main__":
    print(f"Custom Universe: {{len(CUSTOM_UNIVERSE)}} stocks")
    print(f"Average Volatility: {{UNIVERSE_STATS['avg_volatility']}}%")
    print(f"Average Volume: {{UNIVERSE_STATS['avg_volume']:,}}")
'''
        
        with open(filepath, 'w') as f:
            f.write(code)
    
    def create_universe_readme(self, df: pd.DataFrame, filepath: str, timestamp: str):
        """Create a README file for the universe directory"""
        
        readme = f'''# Stock Universe - {timestamp}

## Summary

- **Created:** {timestamp}
- **Total Stocks:** {len(df)}
- **Average Volatility:** {df['volatility'].mean():.2f}%
- **Average Volume:** {int(df['volume'].mean()):,}
- **Price Range:** ${df['price'].min():.2f} - ${df['price'].max():.2f}

---

## Files in This Directory

### 📊 Data Files
- **universe_data.csv** - Complete dataset with all metrics
- **universe_tickers.txt** - Simple list of ticker symbols
- **universe.py** - Python module (importable)

### 📋 Metadata
- **metadata.json** - Structured metadata and statistics
- **README.md** - This file

---

## Top 20 Stocks by Volatility

| Rank | Ticker | Price | Volatility | Volume | Market Cap |
|------|--------|-------|------------|--------|------------|
'''
        
        # Add top 20 stocks
        top_20 = df.nlargest(20, 'volatility')
        rank = 1
        for idx, row in top_20.iterrows():
            readme += f"| {rank} | {row['ticker']} | ${row['price']:.2f} | {row['volatility']:.1f}% | {int(row['volume']):,} | ${row['market_cap']/1e6:.1f}M |\n"
            rank += 1
        
        readme += '''

---

## Usage

```python
from universe import CUSTOM_UNIVERSE
# Use CUSTOM_UNIVERSE list in your scanner
```

'''

        with open(filepath, 'w') as f:
            f.write(readme)


def main():
    """Main entry point for universe building"""
    import argparse

    parser = argparse.ArgumentParser(description='Build stock universe')
    parser.add_argument('--max-tickers', type=int, default=None,
                        help='Max tickers to screen (for testing)')
    parser.add_argument('--top-n', type=int, default=200,
                        help='Number of stocks in final universe')
    args = parser.parse_args()

    builder = UniverseBuilder()

    # Get all tickers
    all_tickers = builder.get_all_market_tickers()

    # Screen universe
    df = builder.batch_screen_universe(all_tickers, max_tickers=args.max_tickers)

    if df.empty:
        print("No stocks passed screening criteria")
        return

    # Apply final filters and rank
    final_df = builder.rank_and_filter_universe(df, top_n=args.top_n)

    # Save universe
    builder.save_universe(final_df)

    print("\n✓ Universe build complete!")


if __name__ == "__main__":
    main()