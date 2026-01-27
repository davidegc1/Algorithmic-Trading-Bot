"""
PRE-MARKET SCANNER
Builds daily watchlist of top 25 gappers for active trading

Schedule: 8:00 AM - 9:25 AM ET (before market open)
Output: state/daily_watchlist.json

Selection Process:
1. Load base universe (500 stocks or existing universe file)
2. Get prior day close for each stock
3. Get current pre-market price and volume
4. Calculate gap %, relative volume
5. Score and rank all stocks
6. Select top 25 for daily watchlist
7. Record pre-market highs for breakout reference
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

try:
    import alpaca_trade_api as tradeapi
except ImportError:
    tradeapi = None

import pandas as pd

from core.shared_state import get_state_dir, get_logs_dir, SafeJSONFile
from config.config import (
    DAILY_WATCHLIST_SIZE,
    MIN_GAP_PCT,
    MIN_PREMARKET_VOLUME,
    MIN_PREMARKET_REL_VOLUME,
    PRICE_MIN,
    PRICE_MAX,
    UNIVERSE_PATH,
    DEFAULT_UNIVERSE,
)

load_dotenv()

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'premarket.log'), mode='a'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


class PreMarketScanner:
    """
    Pre-market scanner that builds daily watchlist of top gappers
    """

    def __init__(self):
        # API setup
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

        if tradeapi is None:
            raise ImportError("alpaca_trade_api is required. Install with: pip install alpaca-trade-api")

        self.api = tradeapi.REST(
            self.api_key,
            self.api_secret,
            self.base_url,
            api_version='v2'
        )

        # Configuration
        self.WATCHLIST_SIZE = DAILY_WATCHLIST_SIZE
        self.MIN_GAP_PCT = MIN_GAP_PCT
        self.MIN_PM_VOLUME = MIN_PREMARKET_VOLUME
        self.MIN_REL_VOLUME = MIN_PREMARKET_REL_VOLUME
        self.PRICE_MIN = PRICE_MIN
        self.PRICE_MAX = PRICE_MAX

        # File paths
        self.base_universe_file = self._find_base_universe()
        self.watchlist_file = os.path.join(get_state_dir(), 'daily_watchlist.json')

        # Rate limiting
        self.api_call_delay = 0.15  # 150ms between calls to stay under limit

        logger.info("PreMarketScanner initialized")
        logger.info(f"  Watchlist size: {self.WATCHLIST_SIZE}")
        logger.info(f"  Min gap: {self.MIN_GAP_PCT*100:.0f}%")
        logger.info(f"  Min PM volume: {self.MIN_PM_VOLUME:,}")

    def _find_base_universe(self) -> Optional[str]:
        """Find the base universe file"""
        # Check for base universe
        base_path = 'universes/base_universe/base_universe.txt'
        if os.path.exists(base_path):
            logger.info(f"Using base universe: {base_path}")
            return base_path

        # Try configured universe path
        if os.path.exists(UNIVERSE_PATH):
            logger.info(f"Using configured universe: {UNIVERSE_PATH}")
            return UNIVERSE_PATH

        # Fallback to most recent universe
        universes_dir = 'universes'
        if os.path.exists(universes_dir):
            dirs = sorted([d for d in os.listdir(universes_dir)
                          if os.path.isdir(os.path.join(universes_dir, d))],
                         reverse=True)
            for d in dirs:
                ticker_file = os.path.join(universes_dir, d, 'universe_tickers.txt')
                if os.path.exists(ticker_file):
                    logger.info(f"Using fallback universe: {ticker_file}")
                    return ticker_file

        logger.warning("No universe file found, will use DEFAULT_UNIVERSE")
        return None

    def load_base_universe(self) -> List[str]:
        """Load base universe tickers"""
        if self.base_universe_file and os.path.exists(self.base_universe_file):
            with open(self.base_universe_file, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(tickers)} tickers from {self.base_universe_file}")
        else:
            tickers = DEFAULT_UNIVERSE.copy()
            logger.info(f"Using DEFAULT_UNIVERSE with {len(tickers)} tickers")

        return tickers

    def get_prior_close(self, symbol: str) -> Optional[float]:
        """Get yesterday's closing price"""
        try:
            # Get daily bars for last 2 days
            bars = self.api.get_bars(
                symbol,
                '1Day',
                limit=2
            ).df

            if len(bars) >= 1:
                return float(bars.iloc[-1]['close'])
            return None

        except Exception as e:
            logger.debug(f"Error getting prior close for {symbol}: {e}")
            return None

    def get_premarket_data(self, symbol: str) -> Optional[Dict]:
        """
        Get pre-market price, volume, and high

        Returns:
            {
                'price': current pre-market price,
                'volume': pre-market volume,
                'high': pre-market high (for breakout reference)
            }
        """
        try:
            # Get latest quote for current price
            quote = self.api.get_latest_quote(symbol)

            # Handle potential None values
            ask_price = getattr(quote, 'ask_price', 0) or 0
            bid_price = getattr(quote, 'bid_price', 0) or 0

            if ask_price > 0 and bid_price > 0:
                current_price = (ask_price + bid_price) / 2
            elif ask_price > 0:
                current_price = ask_price
            elif bid_price > 0:
                current_price = bid_price
            else:
                return None

            # Get today's minute bars for volume and high
            today_start = datetime.now().replace(hour=4, minute=0, second=0, microsecond=0)

            try:
                bars = self.api.get_bars(
                    symbol,
                    '1Min',
                    start=today_start.isoformat(),
                    limit=500  # Up to 500 minutes of pre-market
                ).df
            except Exception:
                bars = pd.DataFrame()

            if bars.empty:
                return {
                    'price': float(current_price),
                    'volume': 0,
                    'high': float(current_price)
                }

            pm_volume = int(bars['volume'].sum())
            pm_high = float(bars['high'].max())

            return {
                'price': float(current_price),
                'volume': pm_volume,
                'high': max(pm_high, float(current_price))  # Ensure high >= current
            }

        except Exception as e:
            logger.debug(f"Error getting premarket data for {symbol}: {e}")
            return None

    def get_average_volume(self, symbol: str, days: int = 20) -> float:
        """Get average daily volume for relative volume calculation"""
        try:
            bars = self.api.get_bars(symbol, '1Day', limit=days).df
            if not bars.empty:
                return float(bars['volume'].mean())
            return 0
        except Exception:
            return 0

    def calculate_score(
        self,
        gap_pct: float,
        relative_volume: float,
        float_shares: Optional[float] = None
    ) -> float:
        """
        Calculate ranking score for watchlist selection

        Formula: gap% x relative_volume x float_factor
        - Higher gap = higher score
        - Higher relative volume = higher score
        - Lower float = higher score (more explosive potential)
        """
        # Base score: gap x relative volume
        score = gap_pct * relative_volume * 100

        # Float factor (if available): prefer lower float
        if float_shares and float_shares > 0:
            # Normalize: 10M float = 1.0, 50M float = 0.45, 100M float = 0.32
            float_factor = 1 / (float_shares / 10_000_000) ** 0.5
            float_factor = min(float_factor, 2.0)  # Cap at 2x
            score *= float_factor

        return score

    def scan_stock(self, symbol: str, avg_volumes: Dict[str, float]) -> Optional[Dict]:
        """
        Scan a single stock for watchlist inclusion

        Returns stock data if it passes filters, None otherwise
        """
        try:
            # Get prior close
            prior_close = self.get_prior_close(symbol)
            if not prior_close or prior_close <= 0:
                return None

            time.sleep(self.api_call_delay)  # Rate limiting

            # Get pre-market data
            pm_data = self.get_premarket_data(symbol)
            if not pm_data:
                return None

            current_price = pm_data['price']

            # Price filter
            if not (self.PRICE_MIN <= current_price <= self.PRICE_MAX):
                return None

            # Calculate gap
            gap_pct = (current_price - prior_close) / prior_close

            # Gap filter (must be positive and > minimum)
            if gap_pct < self.MIN_GAP_PCT:
                return None

            # Volume filter
            if pm_data['volume'] < self.MIN_PM_VOLUME:
                return None

            # Relative volume
            avg_volume = avg_volumes.get(symbol, 0)
            if avg_volume > 0:
                # Normalize pre-market volume to daily equivalent
                # Pre-market is ~5.5 hours, full day is 6.5 hours
                normalized_pm_vol = pm_data['volume'] * (6.5 / 5.5)
                relative_volume = normalized_pm_vol / avg_volume
            else:
                relative_volume = 1.0

            if relative_volume < self.MIN_REL_VOLUME:
                return None

            # Calculate score
            score = self.calculate_score(gap_pct, relative_volume)

            return {
                'symbol': symbol,
                'prior_close': round(prior_close, 4),
                'premarket_price': round(current_price, 4),
                'premarket_high': round(pm_data['high'], 4),
                'premarket_volume': pm_data['volume'],
                'gap_pct': round(gap_pct, 4),
                'relative_volume': round(relative_volume, 2),
                'score': round(score, 2)
            }

        except Exception as e:
            logger.debug(f"Error scanning {symbol}: {e}")
            return None

    def scan_universe(self) -> List[Dict]:
        """
        Scan entire base universe and return ranked candidates

        Returns:
            List of stock dicts, sorted by score descending
        """
        tickers = self.load_base_universe()

        logger.info(f"Starting pre-market scan of {len(tickers)} stocks...")
        logger.info(f"Criteria: Gap>{self.MIN_GAP_PCT*100}%, PMVol>{self.MIN_PM_VOLUME:,}, RelVol>{self.MIN_REL_VOLUME}x")

        # Pre-fetch average volumes (batch for efficiency)
        logger.info("Fetching average volumes...")
        avg_volumes = {}
        for i, symbol in enumerate(tickers):
            if i % 50 == 0 and i > 0:
                logger.info(f"  Volume fetch progress: {i}/{len(tickers)}")
            avg_volumes[symbol] = self.get_average_volume(symbol)
            time.sleep(self.api_call_delay)  # Rate limiting

        # Scan each stock
        candidates = []
        for i, symbol in enumerate(tickers):
            if i % 25 == 0:
                logger.info(f"  Scan progress: {i}/{len(tickers)} | Found: {len(candidates)} candidates")

            result = self.scan_stock(symbol, avg_volumes)
            if result:
                candidates.append(result)
                logger.info(f"  ✓ {symbol}: Gap={result['gap_pct']*100:.1f}%, "
                           f"RelVol={result['relative_volume']:.1f}x, Score={result['score']:.1f}")

        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Pre-market scan complete: {len(candidates)} candidates found")
        return candidates

    def build_daily_watchlist(self) -> List[Dict]:
        """
        Build the daily watchlist of top N stocks

        Returns:
            List of top stocks for today's trading
        """
        # Scan universe
        candidates = self.scan_universe()

        # Take top N
        watchlist = candidates[:self.WATCHLIST_SIZE]

        # Add rank
        for i, stock in enumerate(watchlist):
            stock['rank'] = i + 1

        logger.info(f"Daily watchlist built: {len(watchlist)} stocks")

        if watchlist:
            logger.info("Top 5 stocks:")
            for stock in watchlist[:5]:
                logger.info(f"  #{stock['rank']}: {stock['symbol']} | "
                           f"Gap={stock['gap_pct']*100:.1f}% | "
                           f"Score={stock['score']:.1f}")

        return watchlist

    def save_watchlist(self, watchlist: List[Dict]):
        """Save watchlist to state file"""
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'market_open': datetime.now().replace(hour=9, minute=30, second=0, microsecond=0).isoformat(),
            'watchlist_size': len(watchlist),
            'selection_criteria': {
                'min_gap_pct': self.MIN_GAP_PCT,
                'min_pm_volume': self.MIN_PM_VOLUME,
                'min_rel_volume': self.MIN_REL_VOLUME,
                'price_range': [self.PRICE_MIN, self.PRICE_MAX]
            },
            'watchlist': watchlist
        }

        # Ensure state directory exists
        state_dir = get_state_dir()
        os.makedirs(state_dir, exist_ok=True)

        # Write atomically
        temp_file = self.watchlist_file + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Rename to final location (atomic on most systems)
        os.replace(temp_file, self.watchlist_file)

        logger.info(f"Watchlist saved to {self.watchlist_file}")

    def load_existing_watchlist(self) -> Optional[Dict]:
        """Load existing watchlist if from today"""
        if not os.path.exists(self.watchlist_file):
            return None

        try:
            with open(self.watchlist_file, 'r') as f:
                data = json.load(f)

            if data.get('date') == datetime.now().strftime('%Y-%m-%d'):
                return data
            return None
        except Exception:
            return None

    def run(self, force: bool = False) -> List[Dict]:
        """
        Main entry point

        Args:
            force: If True, rebuild watchlist even if one exists for today

        Returns:
            The daily watchlist
        """
        logger.info("=" * 80)
        logger.info("PRE-MARKET SCANNER STARTING")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Check for existing watchlist
            if not force:
                existing = self.load_existing_watchlist()
                if existing:
                    logger.info(f"Today's watchlist already exists ({existing['watchlist_size']} stocks)")
                    logger.info("Use force=True to rebuild")
                    return existing.get('watchlist', [])

            # Check market status
            try:
                clock = self.api.get_clock()
                if clock.is_open:
                    logger.warning("Market is already open - pre-market scan may be late")
            except Exception as e:
                logger.warning(f"Could not check market status: {e}")

            # Build watchlist
            watchlist = self.build_daily_watchlist()

            # Save results
            if watchlist:
                self.save_watchlist(watchlist)
            else:
                logger.warning("No stocks passed filters - check criteria or market conditions")

            logger.info("=" * 80)
            logger.info("PRE-MARKET SCANNER COMPLETE")
            logger.info("=" * 80)

            return watchlist

        except Exception as e:
            logger.error(f"Pre-market scanner error: {e}")
            raise


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Pre-market scanner for daily watchlist')
    parser.add_argument('--force', action='store_true', help='Force rebuild even if watchlist exists')
    args = parser.parse_args()

    scanner = PreMarketScanner()
    watchlist = scanner.run(force=args.force)

    if watchlist:
        print(f"\nDaily Watchlist ({len(watchlist)} stocks):")
        print("-" * 60)
        for stock in watchlist:
            print(f"#{stock['rank']:2d} {stock['symbol']:5s} | "
                  f"Gap: {stock['gap_pct']*100:5.1f}% | "
                  f"Vol: {stock['relative_volume']:4.1f}x | "
                  f"Score: {stock['score']:6.1f}")


if __name__ == "__main__":
    main()
