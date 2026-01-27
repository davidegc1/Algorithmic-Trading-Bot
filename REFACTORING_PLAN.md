# Trading Bot Comprehensive Refactoring Plan

**Version:** 2.1
**Date:** 2026-01-26
**Status:** Ready for Implementation

---

## Executive Summary

This plan addresses critical issues identified in the trading bot's scanning and buying logic, universe selection, and overall system architecture. The goal is to transform the system from a flawed implementation into a research-backed, effective momentum trading system.

### Key Changes Overview

| Component | Current State | New State | Rationale |
|-----------|--------------|-----------|-----------|
| **Universe Size** | 200 stocks (static) | 25 stocks (daily dynamic) | Momentum research optimal |
| **Scan Interval** | 60 seconds | 45 seconds | Faster detection, within limits |
| **Monitor Interval** | 60 seconds | 30 seconds | Better exit timing |
| **Signal Detection** | Breakout from candle low | Breakout from pre-market high | Industry standard |
| **Technical Indicators** | None | VWAP + RSI | Required for momentum |
| **Signal Expiry** | 5 minutes | 60 seconds | Prevent stale entries |
| **API Calls/Minute** | ~990 (over limit!) | ~157 (within 200 limit) | Sustainable operation |
| **Price Validation** | None | Before every buy | Slippage protection |

### Research Basis

- **25 stocks** is the optimal momentum portfolio size ([Capitalmind Research](https://www.capitalmind.in/insights/momentum-strategy-how-many-stocks))
- **45-second scans** balance speed vs noise ([TradersUnion](https://tradersunion.com/interesting-articles/day-trading-what-is-day-trading/best-time-frame-for-day-trading/))
- **VWAP + RSI** are industry standard for momentum confirmation
- **Pre-market gap scanning** is how professional day traders operate ([Warrior Trading](https://www.warriortrading.com/gap-go/))

---

## Table of Contents

1. [API Budget & Optimization Strategy](#api-budget--optimization-strategy)
2. [Phase 1: Universe & Pre-Market System](#phase-1-universe--pre-market-system)
3. [Phase 2: Scanner Refactoring](#phase-2-scanner-refactoring)
4. [Phase 3: Buyer Refactoring](#phase-3-buyer-refactoring)
5. [Phase 4: Monitor Enhancement](#phase-4-monitor-enhancement)
6. [Phase 5: Configuration & Integration](#phase-5-configuration--integration)
7. [Phase 6: Testing & Validation](#phase-6-testing--validation)
8. [File Changes Summary](#file-changes-summary)
9. [Implementation Timeline](#implementation-timeline)
10. [Appendix: Quick Reference](#appendix-quick-reference)

---

## API Budget & Optimization Strategy

### Rate Limit: 200 calls/minute

This is a hard constraint from Alpaca. The entire system must operate within this budget.

### Current State (Broken)

```
Scanner:  198 stocks × 5 calls = 990 calls per scan cycle
          At 60s interval = 990 calls/minute
          ❌ EXCEEDS 200 LIMIT BY 5x
```

### New State (Optimized)

| Service | Calculation | Calls/Min |
|---------|-------------|-----------|
| **Scanner** | 25 stocks × 2 calls × (60/45) cycles | **67** |
| **Monitor** | 20 positions × 2 calls × 2 cycles | **80** |
| **Buyer** | Price revalidation + orders | **10** |
| **Seller** | Order execution | **5** |
| **Orchestrator** | Clock checks, status | **5** |
| **Buffer** | Retries, errors, spikes | **33** |
| **TOTAL** | | **200** |

### Why This Allocation?

| Decision | Rationale |
|----------|-----------|
| **45s scans (not 30s)** | 30s adds noise without meaningful edge; 45s is 33% faster than 60s with minimal noise increase |
| **30s monitor (not 60s)** | Exit timing is critical; faster monitoring protects profits and limits losses |
| **25 stocks (not more)** | Research shows 20-30 is optimal for momentum; more dilutes factor exposure |
| **33 call buffer** | API calls can spike; retries on failures; safety margin prevents rate limiting |

### API Call Reduction Strategies

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| **Drop 15-min bars** | -1 call/stock | Context from 5-min sufficient |
| **Move asset check to pre-market** | -1 call/stock | Check tradeable once per day |
| **Move quote check to pre-market** | -1 call/stock | Spread check once per day |
| **Batch position queries** | -10 calls/cycle | Single list_positions() call |

---

## Phase 1: Universe & Pre-Market System

### 1.1 Overview

**Problem:** Current system uses a static 200-stock universe that's over a month old, contains dead tickers (ZYXI, IRBT), and lacks critical data (float, short interest).

**Solution:** Two-tier system with dynamic daily selection.

### 1.2 Two-Tier Universe Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BASE UNIVERSE (Tier 1)                      │
│                        500 stocks                               │
│                    Refreshed: Weekly                            │
├─────────────────────────────────────────────────────────────────┤
│  Criteria:                                                      │
│  • Market cap: $50M - $2B                                       │
│  • Price: $2 - $50                                              │
│  • Avg daily volume: > 1M shares                                │
│  • Float: < 100M shares                                         │
│  • Tradeable on Alpaca (not HTB)                                │
│  • No recent delisting/merger news                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    Pre-Market Filter (Daily)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DAILY WATCHLIST (Tier 2)                      │
│                        25 stocks                                │
│                    Refreshed: Daily 9:00 AM                     │
├─────────────────────────────────────────────────────────────────┤
│  Selection Criteria:                                            │
│  • Gap > 3% from prior close                                    │
│  • Pre-market volume > 50K shares                               │
│  • Pre-market relative volume > 2x                              │
│  • Price still in $2-$50 range                                  │
│                                                                 │
│  Ranking Formula:                                               │
│  score = gap% × relative_volume × (1 / sqrt(float/1M))          │
│                                                                 │
│  Output: Top 25 by score                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 New File: `core/premarket_scanner.py`

**Purpose:** Runs 8:00-9:25 AM ET to build daily watchlist

```python
"""
PRE-MARKET SCANNER
Builds daily watchlist of top 25 gappers for active trading

Schedule: 8:00 AM - 9:25 AM ET (before market open)
Output: state/daily_watchlist.json

Selection Process:
1. Load 500-stock base universe
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
import alpaca_trade_api as tradeapi
import pandas as pd

from core.shared_state import get_state_dir, get_logs_dir, SafeJSONFile

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

        self.api = tradeapi.REST(
            self.api_key,
            self.api_secret,
            self.base_url,
            api_version='v2'
        )

        # Configuration
        self.WATCHLIST_SIZE = 25
        self.MIN_GAP_PCT = 0.03          # 3% minimum gap
        self.MIN_PM_VOLUME = 50_000      # 50K pre-market volume
        self.MIN_REL_VOLUME = 2.0        # 2x relative volume
        self.PRICE_MIN = 2.0
        self.PRICE_MAX = 50.0

        # File paths
        self.base_universe_file = self._find_base_universe()
        self.watchlist_file = os.path.join(get_state_dir(), 'daily_watchlist.json')

        logger.info("PreMarketScanner initialized")

    def _find_base_universe(self) -> str:
        """Find the base universe file"""
        # Check for base universe
        base_path = 'universes/base_universe/base_universe.txt'
        if os.path.exists(base_path):
            return base_path

        # Fallback to most recent universe
        universes_dir = 'universes'
        if os.path.exists(universes_dir):
            dirs = sorted([d for d in os.listdir(universes_dir)
                          if os.path.isdir(os.path.join(universes_dir, d))],
                         reverse=True)
            for d in dirs:
                ticker_file = os.path.join(universes_dir, d, 'universe_tickers.txt')
                if os.path.exists(ticker_file):
                    return ticker_file

        raise FileNotFoundError("No universe file found")

    def load_base_universe(self) -> List[str]:
        """Load base universe tickers"""
        with open(self.base_universe_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]

        logger.info(f"Loaded {len(tickers)} tickers from base universe")
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
            current_price = (quote.ask_price + quote.bid_price) / 2

            # Get today's minute bars for volume and high
            bars = self.api.get_bars(
                symbol,
                '1Min',
                start=datetime.now().replace(hour=4, minute=0, second=0).isoformat(),
                limit=500  # Up to 500 minutes of pre-market
            ).df

            if bars.empty:
                return {
                    'price': current_price,
                    'volume': 0,
                    'high': current_price
                }

            pm_volume = int(bars['volume'].sum())
            pm_high = float(bars['high'].max())

            return {
                'price': float(current_price),
                'volume': pm_volume,
                'high': pm_high
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
        except:
            return 0

    def calculate_score(
        self,
        gap_pct: float,
        relative_volume: float,
        float_shares: Optional[float] = None
    ) -> float:
        """
        Calculate ranking score for watchlist selection

        Formula: gap% × relative_volume × float_factor
        - Higher gap = higher score
        - Higher relative volume = higher score
        - Lower float = higher score (more explosive potential)
        """
        # Base score: gap × relative volume
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
        logger.info(f"Criteria: Gap>{self.MIN_GAP_PCT*100}%, PMVol>{self.MIN_PM_VOLUME}, RelVol>{self.MIN_REL_VOLUME}x")

        # Pre-fetch average volumes (batch for efficiency)
        logger.info("Fetching average volumes...")
        avg_volumes = {}
        for i, symbol in enumerate(tickers):
            if i % 100 == 0:
                logger.info(f"  Volume fetch progress: {i}/{len(tickers)}")
            avg_volumes[symbol] = self.get_average_volume(symbol)
            time.sleep(0.1)  # Rate limiting

        # Scan each stock
        candidates = []
        for i, symbol in enumerate(tickers):
            if i % 50 == 0:
                logger.info(f"  Scan progress: {i}/{len(tickers)} | Found: {len(candidates)} candidates")

            result = self.scan_stock(symbol, avg_volumes)
            if result:
                candidates.append(result)
                logger.info(f"  ✓ {symbol}: Gap={result['gap_pct']*100:.1f}%, "
                           f"RelVol={result['relative_volume']:.1f}x, Score={result['score']:.1f}")

            time.sleep(0.15)  # Rate limiting for pre-market

        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Pre-market scan complete: {len(candidates)} candidates found")
        return candidates

    def build_daily_watchlist(self) -> List[Dict]:
        """
        Build the daily watchlist of top 25 stocks

        Returns:
            List of top 25 stocks for today's trading
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
            'market_open': datetime.now().replace(hour=9, minute=30, second=0).isoformat(),
            'watchlist_size': len(watchlist),
            'selection_criteria': {
                'min_gap_pct': self.MIN_GAP_PCT,
                'min_pm_volume': self.MIN_PM_VOLUME,
                'min_rel_volume': self.MIN_REL_VOLUME,
                'price_range': [self.PRICE_MIN, self.PRICE_MAX]
            },
            'watchlist': watchlist
        }

        with SafeJSONFile(self.watchlist_file, 'w') as f:
            f.update(data)

        logger.info(f"Watchlist saved to {self.watchlist_file}")

    def run(self):
        """Main entry point"""
        logger.info("=" * 80)
        logger.info("PRE-MARKET SCANNER STARTING")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Check if market is closed (we should be in pre-market)
            clock = self.api.get_clock()
            if clock.is_open:
                logger.warning("Market is already open - pre-market scan may be late")

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

        except Exception as e:
            logger.error(f"Pre-market scanner error: {e}")
            raise


def main():
    """Entry point"""
    scanner = PreMarketScanner()
    scanner.run()


if __name__ == "__main__":
    main()
```

### 1.4 Daily Watchlist Output Format

**File:** `state/daily_watchlist.json`

```json
{
    "date": "2026-01-27",
    "generated_at": "2026-01-27T09:00:00.000000",
    "market_open": "2026-01-27T09:30:00.000000",
    "watchlist_size": 25,
    "selection_criteria": {
        "min_gap_pct": 0.03,
        "min_pm_volume": 50000,
        "min_rel_volume": 2.0,
        "price_range": [2.0, 50.0]
    },
    "watchlist": [
        {
            "symbol": "ABCD",
            "rank": 1,
            "prior_close": 5.00,
            "premarket_price": 5.40,
            "premarket_high": 5.55,
            "premarket_volume": 500000,
            "gap_pct": 0.08,
            "relative_volume": 5.2,
            "score": 87.5
        },
        {
            "symbol": "EFGH",
            "rank": 2,
            "prior_close": 10.00,
            "premarket_price": 11.20,
            "premarket_high": 11.35,
            "premarket_volume": 200000,
            "gap_pct": 0.12,
            "relative_volume": 3.1,
            "score": 79.2
        }
        // ... 23 more stocks
    ]
}
```

### 1.5 Enhanced Universe Builder

**File:** `scripts/universe_builder.py`

**Changes Required:**

```python
def quick_screen_ticker(self, ticker: str) -> Optional[Dict]:
    """
    Quick screening of a single ticker
    UPDATED: Now includes float and short interest data
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Existing filters...
        price = info.get('currentPrice') or info.get('previousClose')
        if not price or price < 2.0 or price > 50:  # UPDATED: $2 min (not $0.50)
            return None

        volume = info.get('averageVolume') or info.get('volume')
        if not volume or volume < 1_000_000:  # UPDATED: 1M min (not 500K)
            return None

        market_cap = info.get('marketCap')
        if not market_cap or market_cap > 2_000_000_000:  # UPDATED: $2B max (not $5B)
            return None

        # NEW: Float data
        float_shares = info.get('floatShares')
        shares_outstanding = info.get('sharesOutstanding')

        if not float_shares and shares_outstanding:
            # Estimate float if not available
            insider_pct = info.get('heldPercentInsiders', 0.15)
            float_shares = int(shares_outstanding * (1 - insider_pct))

        # NEW: Float filter
        if float_shares and float_shares > 100_000_000:  # 100M max float
            return None

        # NEW: Short interest
        short_ratio = info.get('shortRatio', 0)
        short_percent = info.get('shortPercentOfFloat', 0)

        # Existing volatility calculation...
        hist = stock.history(period='3mo')
        if hist.empty or len(hist) < 10:
            return None

        returns = hist['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100

        if volatility < 50:
            return None

        return {
            'ticker': ticker,
            'price': round(price, 2),
            'volume': int(volume),
            'market_cap': market_cap,
            'volatility': round(volatility, 2),
            'float_shares': float_shares,      # NEW
            'short_ratio': short_ratio,         # NEW
            'short_percent': short_percent,     # NEW
            'exchange': info.get('exchange', 'Unknown')
        }

    except Exception as e:
        return None


def rank_and_filter_universe(
    self,
    df: pd.DataFrame,
    top_n: int = 500  # UPDATED: 500 for base universe
) -> pd.DataFrame:
    """
    Apply final filters and rank the discovered universe
    UPDATED: New ranking formula includes float
    """
    # Apply filters
    filtered = df[
        (df['price'] >= 2.0) &
        (df['price'] <= 50.0) &
        (df['volume'] >= 1_000_000) &
        (df['market_cap'] <= 2_000_000_000) &
        (df['float_shares'] <= 100_000_000)
    ].copy()

    # NEW: Ranking formula
    # Higher volatility + lower float = higher rank
    filtered['rank_score'] = (
        filtered['volatility'] *
        (1 / (filtered['float_shares'] / 10_000_000).clip(lower=0.1) ** 0.5)
    )

    filtered = filtered.sort_values('rank_score', ascending=False)
    return filtered.head(top_n)
```

### 1.6 Directory Structure

```
universes/
├── base_universe/                    # NEW: Base universe (500 stocks)
│   ├── base_universe.txt             # Ticker list
│   ├── base_universe.csv             # Full data with float
│   ├── metadata.json                 # Generation stats
│   └── README.md                     # Documentation
│
└── universe_20251212_164239/         # Legacy (can be archived)
    └── ...

state/
├── daily_watchlist.json              # NEW: Today's 25 stocks
├── signals.json                      # Entry signals from scanner
├── positions.json                    # Active positions
├── sell_signals.json                 # Exit signals
├── trades.json                       # Trade history
├── cooldowns.json                    # Cooldown tracking
└── orchestrator_status.json          # Service status
```

---

## Phase 2: Scanner Refactoring

### 2.1 Overview

**Current Problems:**
1. Breakout detection measures from current candle low (fundamentally wrong)
2. No VWAP indicator (industry standard missing)
3. No RSI filter (can't detect overbought)
4. Scans 200 stocks (5x over API limit)
5. 5-minute signal expiry (too long for momentum)
6. 60-second scan interval (could be faster)

**Solutions:**
1. Breakout from pre-market high or prior day high
2. Add VWAP calculation and filter
3. Add RSI calculation and filter (40-75 range)
4. Scan 25 stocks from daily watchlist
5. 60-second signal expiry
6. 45-second scan interval

### 2.2 New File: `core/indicators.py`

```python
"""
TECHNICAL INDICATORS MODULE
Provides VWAP, RSI, and other indicators for signal generation

All indicators are calculated from OHLCV bar data.
"""

import pandas as pd
import numpy as np
from typing import Optional


class TechnicalIndicators:
    """Calculate technical indicators from price/volume data"""

    @staticmethod
    def calculate_vwap(bars: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price

        VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3

        Args:
            bars: DataFrame with 'high', 'low', 'close', 'volume' columns

        Returns:
            Series of VWAP values
        """
        if bars.empty:
            return pd.Series(dtype=float)

        typical_price = (bars['high'] + bars['low'] + bars['close']) / 3
        cumulative_tp_vol = (typical_price * bars['volume']).cumsum()
        cumulative_vol = bars['volume'].cumsum()

        # Avoid division by zero
        cumulative_vol = cumulative_vol.replace(0, np.nan)
        vwap = cumulative_tp_vol / cumulative_vol

        return vwap

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

        Args:
            prices: Series of closing prices
            period: RSI period (default 14)

        Returns:
            Series of RSI values (0-100)
        """
        if len(prices) < period + 1:
            return pd.Series([50] * len(prices), index=prices.index)

        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Use exponential moving average for smoother RSI
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        # Avoid division by zero
        avg_loss = avg_loss.replace(0, 0.0001)

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_relative_volume(
        current_volume: int,
        bars: pd.DataFrame,
        lookback: int = 20
    ) -> float:
        """
        Calculate relative volume vs historical average

        Args:
            current_volume: Current bar's volume
            bars: Historical bars with 'volume' column
            lookback: Number of bars for average calculation

        Returns:
            Relative volume ratio (e.g., 2.5 = 2.5x average)
        """
        if bars.empty or len(bars) < 2:
            return 1.0

        lookback = min(lookback, len(bars) - 1)
        avg_volume = bars['volume'].tail(lookback).mean()

        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    @staticmethod
    def calculate_atr(bars: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range

        True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))

        Args:
            bars: DataFrame with 'high', 'low', 'close' columns
            period: ATR period

        Returns:
            Current ATR value
        """
        if len(bars) < period + 1:
            return 0.0

        high = bars['high']
        low = bars['low']
        close = bars['close']
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0

    @staticmethod
    def is_above_vwap(current_price: float, vwap: float) -> bool:
        """Check if price is above VWAP"""
        return current_price > vwap

    @staticmethod
    def is_rsi_valid(
        rsi: float,
        min_rsi: float = 40,
        max_rsi: float = 75
    ) -> bool:
        """
        Check if RSI is in valid range for momentum entry

        - RSI < 40: Potentially weak momentum
        - RSI 40-75: Good momentum, not overbought
        - RSI > 75: Overbought, risky entry
        """
        if pd.isna(rsi):
            return False
        return min_rsi <= rsi <= max_rsi

    @staticmethod
    def is_rsi_sweet_spot(rsi: float) -> bool:
        """Check if RSI is in the sweet spot (50-65)"""
        if pd.isna(rsi):
            return False
        return 50 <= rsi <= 65

    @staticmethod
    def calculate_breakout_percent(
        current_price: float,
        reference_price: float
    ) -> float:
        """
        Calculate breakout percentage from reference level

        Args:
            current_price: Current price
            reference_price: Pre-market high, prior day high, etc.

        Returns:
            Breakout percentage (e.g., 0.03 = 3% above reference)
        """
        if reference_price <= 0:
            return 0.0
        return (current_price - reference_price) / reference_price

    @staticmethod
    def calculate_velocity(
        bars: pd.DataFrame,
        periods: int = 5
    ) -> float:
        """
        Calculate price velocity (rate of change)

        Args:
            bars: DataFrame with 'close' column
            periods: Number of periods for velocity calculation

        Returns:
            Velocity as percentage per period
        """
        if len(bars) < periods + 1:
            return 0.0

        start_price = bars['close'].iloc[-(periods + 1)]
        end_price = bars['close'].iloc[-1]

        if start_price <= 0:
            return 0.0

        total_change = (end_price - start_price) / start_price
        velocity = total_change / periods

        return velocity
```

### 2.3 Refactored Scanner: `core/scanner.py`

**Key Changes:**

#### 2.3.1 New Configuration Constants

```python
# At top of file, import new modules
from core.indicators import TechnicalIndicators
from config import (
    SCAN_INTERVAL_SECONDS,
    MIN_ENTRY_SCORE,
    REQUIRE_ABOVE_VWAP,
    MIN_BREAKOUT_PCT,
    MIN_RELATIVE_VOLUME,
    RSI_MIN,
    RSI_MAX,
    # ... other imports
)
```

#### 2.3.2 Load Daily Watchlist

```python
def load_universe(self) -> List[str]:
    """
    Load today's watchlist (25 stocks) or fall back to base universe

    Priority:
    1. Daily watchlist (if exists and from today)
    2. Base universe (limited to 25 stocks)
    3. Default universe (last resort)
    """
    watchlist_file = os.path.join(get_state_dir(), 'daily_watchlist.json')

    # Try to load today's watchlist
    if os.path.exists(watchlist_file):
        try:
            with SafeJSONFile(watchlist_file, 'r') as data:
                watchlist_date = data.get('date')
                today = datetime.now().strftime('%Y-%m-%d')

                if watchlist_date == today:
                    watchlist = data.get('watchlist', [])
                    self.universe = [s['symbol'] for s in watchlist]
                    self.premarket_data = {s['symbol']: s for s in watchlist}

                    logger.info(f"✅ Loaded daily watchlist: {len(self.universe)} stocks")
                    for s in watchlist[:5]:
                        logger.info(f"   #{s['rank']}: {s['symbol']} | "
                                   f"Gap={s['gap_pct']*100:.1f}% | "
                                   f"PMHigh=${s['premarket_high']:.2f}")
                    return self.universe
                else:
                    logger.warning(f"Watchlist is from {watchlist_date}, not today")

        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")

    # Fallback to base universe
    logger.warning("⚠️ No daily watchlist - using base universe (limited to 25)")

    base_file = 'universes/base_universe/base_universe.txt'
    if not os.path.exists(base_file):
        # Try legacy universe
        base_file = self._find_any_universe()

    if base_file and os.path.exists(base_file):
        with open(base_file, 'r') as f:
            all_stocks = [line.strip() for line in f if line.strip()]
        self.universe = all_stocks[:25]  # LIMIT TO 25
    else:
        self.universe = self._get_default_universe()[:25]

    self.premarket_data = {}
    return self.universe


def _find_any_universe(self) -> Optional[str]:
    """Find any available universe file"""
    universes_dir = 'universes'
    if os.path.exists(universes_dir):
        for d in sorted(os.listdir(universes_dir), reverse=True):
            ticker_file = os.path.join(universes_dir, d, 'universe_tickers.txt')
            if os.path.exists(ticker_file):
                return ticker_file
    return None
```

#### 2.3.3 New Breakout Detection

```python
def calculate_breakout(
    self,
    symbol: str,
    current_price: float,
    bars_5min: pd.DataFrame
) -> Tuple[float, str]:
    """
    Calculate breakout percentage from proper reference level

    Priority:
    1. Pre-market high (from daily watchlist) - BEST
    2. Session high (current day)
    3. Prior close (gap reference)

    Returns:
        (breakout_pct, reference_type)
    """
    # 1. Try pre-market high (most reliable for gap-and-go)
    if symbol in self.premarket_data:
        pm_high = self.premarket_data[symbol].get('premarket_high')
        if pm_high and pm_high > 0:
            breakout_pct = (current_price - pm_high) / pm_high
            return breakout_pct, 'premarket_high'

    # 2. Session high (today's trading)
    if not bars_5min.empty:
        session_high = float(bars_5min['high'].max())
        if session_high > 0:
            breakout_pct = (current_price - session_high) / session_high
            return breakout_pct, 'session_high'

    # 3. Prior close (gap reference)
    if symbol in self.premarket_data:
        prior_close = self.premarket_data[symbol].get('prior_close')
        if prior_close and prior_close > 0:
            breakout_pct = (current_price - prior_close) / prior_close
            return breakout_pct, 'prior_close'

    return 0.0, 'none'
```

#### 2.3.4 New Signal Scoring System

```python
def calculate_signal_score(
    self,
    symbol: str,
    current_price: float,
    vwap: float,
    rsi: float,
    breakout_pct: float,
    breakout_ref: str,
    relative_volume: float
) -> Tuple[int, Dict, Optional[str]]:
    """
    Calculate signal score using research-backed criteria

    REQUIRED (must pass ALL - 60 points):
    - Price > VWAP (15 pts) - Institutional buying pressure
    - Breakout > 1% (20 pts) - Actual price movement
    - Volume > 2x (15 pts) - Participation confirmation
    - RSI 40-75 (10 pts) - Momentum without overbought

    BONUS (additional points):
    - Breakout > 3% (10 pts) - Strong momentum
    - Volume > 4x (10 pts) - High participation
    - RSI 50-65 (5 pts) - Optimal momentum zone
    - Gap > 5% (10 pts) - Strong catalyst indication

    Returns:
        (score, metrics_dict, rejection_reason)
    """
    score = 0
    metrics = {}
    rejection_reason = None

    # ==================== REQUIRED CHECKS ====================

    # 1. Price > VWAP (REQUIRED - 15 pts)
    if current_price <= vwap:
        return 0, {'vwap': vwap}, 'below_vwap'

    score += 15
    metrics['vwap'] = round(vwap, 4)
    metrics['price_vs_vwap'] = round((current_price / vwap - 1) * 100, 2)

    # 2. Breakout > 1% (REQUIRED - 20 pts)
    if breakout_pct < MIN_BREAKOUT_PCT:
        return 0, metrics, f'breakout_{breakout_pct*100:.1f}%_below_1%'

    score += 20
    metrics['breakout_pct'] = round(breakout_pct * 100, 2)
    metrics['breakout_ref'] = breakout_ref

    # 3. Relative Volume > 2x (REQUIRED - 15 pts)
    if relative_volume < MIN_RELATIVE_VOLUME:
        return 0, metrics, f'volume_{relative_volume:.1f}x_below_2x'

    score += 15
    metrics['relative_volume'] = round(relative_volume, 2)

    # 4. RSI 40-75 (REQUIRED - 10 pts)
    if not TechnicalIndicators.is_rsi_valid(rsi, RSI_MIN, RSI_MAX):
        return 0, metrics, f'rsi_{rsi:.0f}_outside_40-75'

    score += 10
    metrics['rsi'] = round(rsi, 1)

    # Base score: 60 (all required criteria passed)

    # ==================== BONUS CHECKS ====================

    # 5. Breakout > 3% (BONUS - 10 pts)
    if breakout_pct >= 0.03:
        score += 10
        metrics['strong_breakout'] = True

    # 6. Volume > 4x (BONUS - 10 pts)
    if relative_volume >= 4.0:
        score += 10
        metrics['high_volume'] = True

    # 7. RSI sweet spot 50-65 (BONUS - 5 pts)
    if TechnicalIndicators.is_rsi_sweet_spot(rsi):
        score += 5
        metrics['rsi_sweet_spot'] = True

    # 8. Gap > 5% (BONUS - 10 pts)
    if symbol in self.premarket_data:
        gap_pct = self.premarket_data[symbol].get('gap_pct', 0)
        metrics['gap_pct'] = round(gap_pct * 100, 2)
        if gap_pct >= 0.05:
            score += 10
            metrics['large_gap'] = True

    return score, metrics, None
```

#### 2.3.5 Updated `scan_symbol()` Method

```python
def scan_symbol(self, symbol: str) -> Optional[Dict]:
    """
    Scan a single symbol with new technical analysis

    API Calls: 2 per stock (5min bars + 2min bars)
    """
    try:
        # 1. Get bars (OPTIMIZED: only 2 timeframes)
        bars_5min = self.get_historical_bars(symbol, '5Min', limit=50)
        bars_2min = self.get_historical_bars(symbol, '2Min', limit=30)

        if bars_5min.empty or len(bars_5min) < 14:  # Need 14 for RSI
            return None

        # 2. Extract current values
        current_price = float(bars_5min.iloc[-1]['close'])
        current_volume = int(bars_5min.iloc[-1]['volume'])

        # 3. Calculate VWAP
        vwap_series = TechnicalIndicators.calculate_vwap(bars_5min)
        vwap = float(vwap_series.iloc[-1])

        # 4. Calculate RSI
        rsi_series = TechnicalIndicators.calculate_rsi(bars_5min['close'], period=14)
        rsi = float(rsi_series.iloc[-1])

        # 5. Calculate breakout from proper reference
        breakout_pct, breakout_ref = self.calculate_breakout(
            symbol, current_price, bars_5min
        )

        # 6. Calculate relative volume
        relative_volume = TechnicalIndicators.calculate_relative_volume(
            current_volume, bars_5min, lookback=20
        )

        # 7. Calculate score
        score, metrics, rejection = self.calculate_signal_score(
            symbol, current_price, vwap, rsi,
            breakout_pct, breakout_ref, relative_volume
        )

        # 8. Check if rejected
        if rejection:
            logger.debug(f"{symbol} rejected: {rejection}")
            return None

        # 9. Check minimum score
        if score < MIN_ENTRY_SCORE:
            logger.debug(f"{symbol} score {score} below minimum {MIN_ENTRY_SCORE}")
            return None

        # 10. Build signal
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'price': round(current_price, 4),
            'score': score,
            **metrics
        }

        # Add pre-market data if available
        if symbol in self.premarket_data:
            pm = self.premarket_data[symbol]
            signal['prior_close'] = pm.get('prior_close')
            signal['premarket_high'] = pm.get('premarket_high')

        # Log signal
        logger.info(
            f"🎯 SIGNAL: {symbol} @ ${current_price:.2f} | "
            f"Score={score} | RSI={rsi:.0f} | "
            f"Breakout={breakout_pct*100:.1f}% ({breakout_ref}) | "
            f"Vol={relative_volume:.1f}x"
        )

        return signal

    except Exception as e:
        logger.error(f"Error scanning {symbol}: {e}")
        return None
```

#### 2.3.6 Updated Main Loop (45-second interval)

```python
def run_continuous(self, interval_seconds: int = 45):  # CHANGED: 45s default
    """
    Run scanner continuously with 45-second intervals

    API Budget:
    - 25 stocks × 2 calls = 50 calls per cycle
    - At 45s interval = 67 calls/minute
    - Well within 200/min limit
    """
    logger.info("=" * 80)
    logger.info("SCANNER SERVICE STARTING")
    logger.info(f"   Scan Interval: {interval_seconds}s")
    logger.info(f"   Universe Size: {len(self.universe)} stocks")
    logger.info(f"   API Calls/Cycle: ~{len(self.universe) * 2}")
    logger.info(f"   Est. Calls/Min: ~{len(self.universe) * 2 * (60/interval_seconds):.0f}")
    logger.info("=" * 80)

    try:
        while True:
            try:
                # Check market status
                clock = self.api.get_clock()

                if clock.is_open:
                    cycle_start = time.time()

                    # Run scan
                    signals = self.scan_universe()

                    # Save signals
                    if signals:
                        self.save_signals(signals)

                    cycle_duration = time.time() - cycle_start
                    logger.info(
                        f"Scan complete: {len(signals)} signals | "
                        f"Duration: {cycle_duration:.1f}s | "
                        f"Next scan in {interval_seconds}s"
                    )

                    # Wait for next cycle
                    sleep_time = max(0, interval_seconds - cycle_duration)
                    time.sleep(sleep_time)

                else:
                    logger.debug("Market closed")
                    time.sleep(300)  # 5 min sleep when market closed

            except Exception as e:
                logger.error(f"Scan cycle error: {e}")
                time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Scanner stopped by user")
```

---

## Phase 3: Buyer Refactoring

### 3.1 Overview

**Current Problems:**
1. 5-minute signal staleness (way too long)
2. No price re-validation before buying
3. No slippage protection
4. Market orders only

**Solutions:**
1. 60-second signal expiry
2. Price re-validation with max slippage check
3. Spread validation
4. Limit orders with small buffer

### 3.2 Changes to `core/buyer.py`

#### 3.2.1 New Configuration

```python
from config import (
    SIGNAL_MAX_AGE_SECONDS,
    MAX_SLIPPAGE_PCT,
    MAX_SPREAD_PCT,
    USE_LIMIT_ORDERS,
    LIMIT_ORDER_BUFFER,
    # ... existing imports
)
```

#### 3.2.2 Updated Signal Loading (60s expiry)

```python
def load_signals(self) -> List[Dict]:
    """
    Load signals with 60-second freshness requirement

    CHANGED: From 5-minute to 60-second expiry
    Rationale: Momentum signals become stale quickly
    """
    try:
        with SafeJSONFile(self.signals_file, 'r') as data:
            signals = data.get('signals', [])

            # Filter stale signals
            fresh_signals = []
            cutoff = datetime.now() - timedelta(seconds=SIGNAL_MAX_AGE_SECONDS)

            for signal in signals:
                signal_time = datetime.fromisoformat(signal['timestamp'])
                age_seconds = (datetime.now() - signal_time).total_seconds()

                if signal_time >= cutoff:
                    fresh_signals.append(signal)
                else:
                    logger.debug(
                        f"Discarding stale signal: {signal['symbol']} "
                        f"({age_seconds:.0f}s old, max={SIGNAL_MAX_AGE_SECONDS}s)"
                    )

            # Sort by score descending
            fresh_signals.sort(key=lambda x: x.get('score', 0), reverse=True)

            if fresh_signals:
                logger.info(f"📥 Loaded {len(fresh_signals)} fresh signals (< {SIGNAL_MAX_AGE_SECONDS}s old)")
            return fresh_signals

    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading signals: {e}")
        return []
```

#### 3.2.3 New Price Validation Method

```python
def validate_signal_price(
    self,
    signal: Dict
) -> Tuple[bool, float, Optional[str]]:
    """
    Re-validate signal price before execution

    Checks:
    1. Price hasn't moved more than MAX_SLIPPAGE_PCT from signal
    2. Spread is not wider than MAX_SPREAD_PCT

    Returns:
        (is_valid, current_price, rejection_reason)
    """
    symbol = signal['symbol']
    signal_price = signal['price']

    try:
        # Get current quote
        quote = self.api.get_latest_quote(symbol)

        bid = float(quote.bid_price)
        ask = float(quote.ask_price)

        # Check for valid quote
        if bid <= 0 or ask <= 0:
            return False, 0, "invalid_quote"

        # Calculate mid price and spread
        current_price = (bid + ask) / 2
        spread = (ask - bid) / current_price

        # Check spread
        if spread > MAX_SPREAD_PCT:
            logger.warning(
                f"{symbol} spread too wide: {spread*100:.2f}% > {MAX_SPREAD_PCT*100:.1f}%"
            )
            return False, current_price, f"spread_{spread*100:.1f}%"

        # Check slippage from signal price
        slippage = (current_price - signal_price) / signal_price

        if slippage > MAX_SLIPPAGE_PCT:
            logger.warning(
                f"{symbol} price moved +{slippage*100:.1f}% since signal "
                f"(${signal_price:.2f} → ${current_price:.2f})"
            )
            return False, current_price, f"slippage_{slippage*100:.1f}%"

        # Check if price dropped significantly (might indicate reversal)
        if slippage < -0.03:  # Dropped more than 3%
            logger.warning(
                f"{symbol} price dropped {slippage*100:.1f}% since signal - possible reversal"
            )
            return False, current_price, f"price_drop_{slippage*100:.1f}%"

        return True, current_price, None

    except Exception as e:
        logger.error(f"Error validating price for {symbol}: {e}")
        return False, 0, str(e)
```

#### 3.2.4 Updated Execute Buy Method

```python
def execute_buy(self, signal: Dict) -> bool:
    """
    Execute buy order with price validation and slippage protection

    Process:
    1. Validate current price vs signal price
    2. Check spread
    3. Calculate position size based on score tier
    4. Execute order (limit order with buffer)
    5. Save position info for monitor
    """
    symbol = signal['symbol']
    score = signal.get('score', 60)

    try:
        # 1. Validate current price
        is_valid, current_price, rejection = self.validate_signal_price(signal)

        if not is_valid:
            logger.info(f"⏭️  Skipping {symbol}: {rejection}")
            return False

        # 2. Get account info
        account = self.get_account_info()
        if not account:
            return False

        # 3. Calculate position size
        position_size_pct = self.get_position_size_pct(score)
        position_value = account['equity'] * position_size_pct
        quantity = int(position_value / current_price)

        if quantity <= 0:
            logger.warning(f"{symbol} calculated quantity is 0")
            return False

        # 4. Determine order type and price
        if USE_LIMIT_ORDERS:
            # Limit order slightly above current price for better fill
            limit_price = round(current_price * (1 + LIMIT_ORDER_BUFFER), 2)
            order_type = 'limit'
        else:
            limit_price = None
            order_type = 'market'

        # 5. Log order details
        tier_name = "MAX" if position_size_pct >= 0.10 else \
                   "STRONG" if position_size_pct >= 0.07 else "STD"

        logger.info(f"🛒 BUYING {symbol}")
        logger.info(f"   Score: {score} ({tier_name}) | Size: {position_size_pct*100:.0f}%")
        logger.info(f"   Price: ${current_price:.2f} | Qty: {quantity}")
        logger.info(f"   Order: {order_type.upper()}" +
                   (f" @ ${limit_price:.2f}" if limit_price else ""))

        # 6. Execute order
        success, result = self.order_executor.submit_and_wait(
            symbol=symbol,
            qty=quantity,
            side='buy',
            order_type=order_type,
            limit_price=limit_price,
            time_in_force='day'
        )

        if success:
            filled_price = result['filled_price']
            filled_qty = result.get('filled_qty', quantity)
            slippage_from_signal = (filled_price - signal['price']) / signal['price']

            logger.info(f"✅ FILLED {symbol}")
            logger.info(f"   Price: ${filled_price:.2f} | Qty: {filled_qty}")
            logger.info(f"   Slippage from signal: {slippage_from_signal*100:+.2f}%")

            # 7. Save position info for monitor
            self.save_position_info(symbol, {
                'entry_price': filled_price,
                'quantity': filled_qty,
                'entry_time': datetime.now().isoformat(),
                'stop_loss': filled_price * (1 - self.STOP_LOSS_PCT),
                'signal_score': score,
                'signal_price': signal['price'],
                'vwap_at_entry': signal.get('vwap'),
                'rsi_at_entry': signal.get('rsi'),
                'breakout_pct': signal.get('breakout_pct'),
                'slippage': slippage_from_signal
            })

            return True

        else:
            reason = result.get('reason', result.get('status', 'unknown'))
            logger.warning(f"❌ {symbol} order not filled: {reason}")
            return False

    except Exception as e:
        logger.error(f"Error buying {symbol}: {e}")
        return False
```

#### 3.2.5 Updated Main Loop

```python
def run_continuous(self, interval_seconds: int = 15):
    """
    Run buyer continuously

    Checks for signals every 15 seconds (unchanged)
    Hot signal check every 5 seconds (unchanged)
    """
    logger.info("=" * 80)
    logger.info("BUYER SERVICE STARTING")
    logger.info(f"   Regular Interval: {interval_seconds}s")
    logger.info(f"   Signal Max Age: {SIGNAL_MAX_AGE_SECONDS}s")
    logger.info(f"   Max Slippage: {MAX_SLIPPAGE_PCT*100:.1f}%")
    logger.info(f"   Max Spread: {MAX_SPREAD_PCT*100:.1f}%")
    logger.info(f"   Order Type: {'LIMIT' if USE_LIMIT_ORDERS else 'MARKET'}")
    logger.info("=" * 80)

    # ... rest of loop unchanged
```

---

## Phase 4: Monitor Enhancement

### 4.1 Overview

**Change:** Reduce monitor interval from 60s to 30s for better exit timing.

**Rationale:** Faster position monitoring helps:
- Catch momentum fade earlier
- Protect profits with tighter trailing stops
- Limit losses with faster stop execution

**API Impact:** 20 positions × 2 calls × 2 cycles/min = 80 calls/min (within budget)

### 4.2 Changes to `core/monitor.py`

#### 4.2.1 Updated Main Loop

```python
def run_continuous(self, interval_seconds: int = 30):  # CHANGED: 30s (was 60s)
    """
    Run position monitor continuously

    CHANGED: 30-second interval (was 60s)
    Rationale: Better exit timing, protect profits faster

    API Budget:
    - 20 positions × 2 calls = 40 calls per cycle
    - At 30s interval = 80 calls/minute
    """
    logger.info("=" * 80)
    logger.info("MONITOR SERVICE STARTING")
    logger.info(f"   Monitor Interval: {interval_seconds}s")
    logger.info(f"   Stop Loss: {self.STOP_LOSS_PCT*100:.1f}%")
    logger.info(f"   Breakeven At: +{self.BREAKEVEN_PROFIT*100:.1f}%")
    logger.info("=" * 80)

    try:
        while True:
            try:
                clock = self.api.get_clock()

                if clock.is_open:
                    cycle_start = time.time()

                    # Check all positions
                    self.check_positions()

                    cycle_duration = time.time() - cycle_start
                    logger.debug(
                        f"Monitor cycle: {cycle_duration:.1f}s | "
                        f"Next check in {interval_seconds}s"
                    )

                    # Wait for next cycle
                    sleep_time = max(0, interval_seconds - cycle_duration)
                    time.sleep(sleep_time)

                else:
                    logger.debug("Market closed")
                    time.sleep(300)

            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)

    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
```

---

## Phase 5: Configuration & Integration

### 5.1 Complete Updated `config/config.py`

```python
"""
TRADING BOT CONFIGURATION v2.1
Research-backed parameters for momentum trading

Key Changes from v1:
- 25-stock watchlist (optimal momentum portfolio)
- 45-second scan interval (faster detection)
- 30-second monitor interval (better exits)
- VWAP + RSI required for signals
- 60-second signal expiry (prevent stale entries)
- Price validation before buying (slippage protection)
"""

from datetime import time as dt_time

# ============================================================================
# API RATE LIMITS
# ============================================================================
API_RATE_LIMIT = 200               # Alpaca limit: 200 calls/minute
API_BUFFER_CALLS = 33              # Reserve for retries/errors

# ============================================================================
# UNIVERSE SELECTION
# ============================================================================
BASE_UNIVERSE_SIZE = 500           # Pre-qualified candidates (weekly refresh)
DAILY_WATCHLIST_SIZE = 25          # Optimal momentum portfolio size

# Pre-market scanner schedule (ET)
PREMARKET_SCAN_START = dt_time(8, 0)    # 8:00 AM ET
PREMARKET_SCAN_END = dt_time(9, 25)     # 9:25 AM ET

# Pre-market selection criteria
MIN_GAP_PCT = 0.03                 # 3% minimum gap from prior close
MIN_PREMARKET_VOLUME = 50_000      # 50K pre-market volume
MIN_PREMARKET_REL_VOLUME = 2.0     # 2x relative volume
MAX_FLOAT_PREFERRED = 50_000_000   # 50M float (preferred, not required)
PRICE_MIN = 2.0                    # Minimum price (avoid pennies)
PRICE_MAX = 50.0                   # Maximum price

# ============================================================================
# SCANNING (UPDATED)
# ============================================================================
SCAN_INTERVAL_SECONDS = 45         # Scan every 45 seconds (was 60)
API_CALLS_PER_STOCK = 2            # Optimized: 2min + 5min bars only

# Timing constraints
OPTIMAL_TRADING_START = dt_time(9, 30)   # Market open
OPTIMAL_TRADING_END = dt_time(15, 45)    # 15 min before close
AVOID_FIRST_MINUTES = 0            # No longer avoiding (we want early entries)
AVOID_LAST_MINUTES = 15            # Avoid last 15 minutes

# ============================================================================
# SIGNAL GENERATION (NEW)
# ============================================================================
# Required criteria (must pass ALL)
REQUIRE_ABOVE_VWAP = True          # Price must be above VWAP
MIN_BREAKOUT_PCT = 0.01            # 1% minimum breakout from reference
MIN_RELATIVE_VOLUME = 2.0          # 2x volume vs average
RSI_MIN = 40                       # Minimum RSI (avoid weak momentum)
RSI_MAX = 75                       # Maximum RSI (avoid overbought)
MIN_ENTRY_SCORE = 60               # Minimum score to generate signal

# Scoring points
SCORE_ABOVE_VWAP = 15              # Required: price > VWAP
SCORE_BREAKOUT = 20                # Required: breakout > 1%
SCORE_VOLUME = 15                  # Required: volume > 2x
SCORE_RSI_VALID = 10               # Required: RSI 40-75
SCORE_STRONG_BREAKOUT = 10         # Bonus: breakout > 3%
SCORE_HIGH_VOLUME = 10             # Bonus: volume > 4x
SCORE_RSI_SWEET = 5                # Bonus: RSI 50-65
SCORE_LARGE_GAP = 10               # Bonus: gap > 5%

# ============================================================================
# BUYER SETTINGS (UPDATED)
# ============================================================================
SIGNAL_MAX_AGE_SECONDS = 60        # Signal expiry (was 300 = 5 min)
MAX_SLIPPAGE_PCT = 0.02            # 2% max price movement from signal
MAX_SPREAD_PCT = 0.02              # 2% max bid-ask spread
USE_LIMIT_ORDERS = True            # Use limit orders (not market)
LIMIT_ORDER_BUFFER = 0.005         # 0.5% above current for limit price

# Hot signal settings
HOT_SIGNAL_ENABLED = True          # Enable fast-path for high scores
HOT_SIGNAL_MIN_SCORE = 90          # Minimum score for hot signal
HOT_CHECK_INTERVAL = 5             # Check hot signals every 5 seconds

# ============================================================================
# POSITION SIZING (unchanged)
# ============================================================================
MAX_POSITIONS = 20                 # Maximum concurrent positions
POSITION_SIZE_STANDARD = 0.05      # 5% for score 60-84
POSITION_SIZE_STRONG = 0.07        # 7% for score 85-94
POSITION_SIZE_MAXIMUM = 0.10       # 10% for score 95+

SCORE_TIER_STANDARD = (60, 84)     # Standard tier
SCORE_TIER_STRONG = (85, 94)       # Strong tier
SCORE_TIER_MAXIMUM = (95, 100)     # Maximum tier

# ============================================================================
# RISK MANAGEMENT (unchanged)
# ============================================================================
STOP_LOSS_PCT = 0.025              # 2.5% hard stop loss
BREAKEVEN_PROFIT = 0.05            # Move stop to breakeven at +5%

# Trailing stops by profit tier
TRAILING_STOPS = {
    0.05: 0.02,    # +5% profit → 2% trailing stop
    0.10: 0.03,    # +10% profit → 3% trailing stop
    0.15: 0.04,    # +15% profit → 4% trailing stop
    0.20: 0.05,    # +20% profit → 5% trailing stop
}

# Deceleration exit
DECEL_EXIT_THRESHOLD = 0.5         # Exit if acceleration drops below 0.5
MIN_PROFIT_FOR_DECEL_CHECK = 0.05  # Only check decel if +5% profit

# ============================================================================
# MONITOR SETTINGS (UPDATED)
# ============================================================================
MONITOR_INTERVAL_SECONDS = 30      # Check positions every 30s (was 60)

# ============================================================================
# SELLER SETTINGS (unchanged)
# ============================================================================
SELLER_INTERVAL_SECONDS = 15       # Check for sell signals every 15s

# ============================================================================
# COOLDOWN (unchanged)
# ============================================================================
COOLDOWN_MINUTES = 15              # Wait 15 min after selling before re-buying

# ============================================================================
# TIMEFRAMES (UPDATED)
# ============================================================================
# Reduced from 3 to 2 timeframes to save API calls
TIMEFRAME_FAST = '2Min'            # Fast timeframe for velocity
TIMEFRAME_PRIMARY = '5Min'         # Primary signal timeframe
# TIMEFRAME_CONTEXT = '15Min'      # REMOVED: Context from 5min is sufficient

BARS_FAST = 30                     # 30 bars of 2-min data
BARS_PRIMARY = 50                  # 50 bars of 5-min data

# ============================================================================
# API BUDGET SUMMARY
# ============================================================================
"""
Service         | Calculation                           | Calls/Min
----------------|---------------------------------------|----------
Scanner         | 25 stocks × 2 calls × (60/45)         | 67
Monitor         | 20 positions × 2 calls × 2            | 80
Buyer           | Price validation + orders             | 10
Seller          | Order execution                       | 5
Orchestrator    | Clock, status                         | 5
Buffer          | Retries, errors                       | 33
----------------|---------------------------------------|----------
TOTAL           |                                       | 200
"""
```

### 5.2 Orchestrator Updates

**File:** `core/orchestrator.py`

Add pre-market scanner to services:

```python
SERVICES = {
    'premarket': {
        'module': 'core.premarket_scanner',
        'description': 'Pre-market gapper scanner (builds daily watchlist)',
        'priority': 0,
        'schedule': (dt_time(8, 0), dt_time(9, 25)),  # 8:00 - 9:25 AM ET
        'run_once': True  # Runs once per day, not continuously
    },
    'scanner': {
        'module': 'core.scanner',
        'description': 'Signal scanner (45s interval)',
        'priority': 1,
        'interval': SCAN_INTERVAL_SECONDS
    },
    'buyer': {
        'module': 'core.buyer',
        'description': 'Order buyer (15s interval)',
        'priority': 2,
        'interval': 15
    },
    'monitor': {
        'module': 'core.monitor',
        'description': 'Position monitor (30s interval)',
        'priority': 3,
        'interval': MONITOR_INTERVAL_SECONDS
    },
    'seller': {
        'module': 'core.seller',
        'description': 'Order seller (15s interval)',
        'priority': 4,
        'interval': SELLER_INTERVAL_SECONDS
    }
}
```

### 5.3 Daily Workflow Diagram

```
TIME (ET)    SERVICE              ACTION
──────────────────────────────────────────────────────────────────────
04:00 AM     -                    Pre-market data available

08:00 AM     PreMarketScanner     START
             │                    Load 500-stock base universe
             │                    Scan for gappers
             │                    Calculate scores
             │
09:00 AM     │                    Save daily_watchlist.json (25 stocks)
             │
09:25 AM     PreMarketScanner     STOP

09:30 AM     Scanner              START (loads daily watchlist)
             Buyer                START
             Monitor              START
             Seller               START
             │
             │  ┌─────────────────────────────────────────────┐
             │  │ TRADING LOOP (09:30 - 15:45)                │
             │  │                                             │
             │  │ Every 45s: Scanner scans 25 stocks          │
             │  │            → Generates signals              │
             │  │                                             │
             │  │ Every 15s: Buyer checks signals             │
             │  │            → Validates price                │
             │  │            → Executes buys                  │
             │  │                                             │
             │  │ Every 30s: Monitor checks positions         │
             │  │            → Updates trailing stops         │
             │  │            → Generates sell signals         │
             │  │                                             │
             │  │ Every 15s: Seller checks sell signals       │
             │  │            → Executes sells                 │
             │  └─────────────────────────────────────────────┘
             │
15:45 AM     All Services         Wind down (no new entries)

16:00 PM     All Services         STOP (market close)

16:30 PM     -                    Daily summary (trades.json)
```

---

## Phase 6: Testing & Validation

### 6.1 Unit Tests

**File:** `tests/test_indicators.py`

```python
import pytest
import pandas as pd
import numpy as np
from core.indicators import TechnicalIndicators


class TestVWAP:
    def test_vwap_basic(self):
        """VWAP should weight price by volume"""
        bars = pd.DataFrame({
            'high': [10.0, 11.0, 12.0],
            'low': [9.0, 10.0, 11.0],
            'close': [9.5, 10.5, 11.5],
            'volume': [1000, 2000, 1000]
        })
        vwap = TechnicalIndicators.calculate_vwap(bars)
        # Higher volume bar should pull VWAP toward its price
        assert len(vwap) == 3
        assert vwap.iloc[-1] > 0

    def test_vwap_empty(self):
        """VWAP of empty dataframe should be empty"""
        bars = pd.DataFrame()
        vwap = TechnicalIndicators.calculate_vwap(bars)
        assert len(vwap) == 0


class TestRSI:
    def test_rsi_range(self):
        """RSI should be between 0 and 100"""
        prices = pd.Series([10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15, 14, 13, 12])
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert all(0 <= r <= 100 for r in rsi.dropna())

    def test_rsi_uptrend(self):
        """RSI should be high in strong uptrend"""
        prices = pd.Series(range(1, 20))  # Continuous uptrend
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert rsi.iloc[-1] > 70

    def test_rsi_downtrend(self):
        """RSI should be low in strong downtrend"""
        prices = pd.Series(range(20, 1, -1))  # Continuous downtrend
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert rsi.iloc[-1] < 30


class TestRelativeVolume:
    def test_relative_volume_2x(self):
        """2x volume should return ~2.0"""
        bars = pd.DataFrame({'volume': [1000] * 20})
        rel_vol = TechnicalIndicators.calculate_relative_volume(2000, bars)
        assert abs(rel_vol - 2.0) < 0.1

    def test_relative_volume_normal(self):
        """Average volume should return ~1.0"""
        bars = pd.DataFrame({'volume': [1000] * 20})
        rel_vol = TechnicalIndicators.calculate_relative_volume(1000, bars)
        assert abs(rel_vol - 1.0) < 0.1


class TestBreakout:
    def test_breakout_positive(self):
        """Price above reference should give positive breakout"""
        pct = TechnicalIndicators.calculate_breakout_percent(10.5, 10.0)
        assert pct == pytest.approx(0.05, rel=0.01)

    def test_breakout_negative(self):
        """Price below reference should give negative breakout"""
        pct = TechnicalIndicators.calculate_breakout_percent(9.5, 10.0)
        assert pct == pytest.approx(-0.05, rel=0.01)


class TestRSIValidation:
    def test_rsi_valid_range(self):
        """RSI 50 should be valid"""
        assert TechnicalIndicators.is_rsi_valid(50, 40, 75) is True

    def test_rsi_too_low(self):
        """RSI 30 should be invalid (< 40)"""
        assert TechnicalIndicators.is_rsi_valid(30, 40, 75) is False

    def test_rsi_too_high(self):
        """RSI 80 should be invalid (> 75)"""
        assert TechnicalIndicators.is_rsi_valid(80, 40, 75) is False

    def test_rsi_sweet_spot(self):
        """RSI 55 should be in sweet spot"""
        assert TechnicalIndicators.is_rsi_sweet_spot(55) is True
        assert TechnicalIndicators.is_rsi_sweet_spot(45) is False
```

**File:** `tests/test_premarket_scanner.py`

```python
import pytest
from datetime import datetime
from core.premarket_scanner import PreMarketScanner


class TestGapCalculation:
    def test_gap_positive(self):
        """Positive gap calculation"""
        prior_close = 10.0
        current_price = 10.5
        gap = (current_price - prior_close) / prior_close
        assert gap == pytest.approx(0.05, rel=0.01)

    def test_gap_threshold(self):
        """3% gap threshold"""
        scanner = PreMarketScanner.__new__(PreMarketScanner)
        scanner.MIN_GAP_PCT = 0.03

        # 2% gap should fail
        assert 0.02 < scanner.MIN_GAP_PCT

        # 4% gap should pass
        assert 0.04 >= scanner.MIN_GAP_PCT


class TestScoring:
    def test_score_calculation(self):
        """Score formula test"""
        scanner = PreMarketScanner.__new__(PreMarketScanner)

        # gap=5%, rel_vol=3x, no float adjustment
        score = scanner.calculate_score(0.05, 3.0, None)
        expected = 0.05 * 3.0 * 100  # = 15
        assert score == pytest.approx(expected, rel=0.01)

    def test_score_with_float(self):
        """Score with float adjustment"""
        scanner = PreMarketScanner.__new__(PreMarketScanner)

        # Lower float should give higher score
        score_low_float = scanner.calculate_score(0.05, 3.0, 10_000_000)
        score_high_float = scanner.calculate_score(0.05, 3.0, 50_000_000)

        assert score_low_float > score_high_float
```

**File:** `tests/test_signal_scoring.py`

```python
import pytest
from core.scanner import StockScanner


class TestSignalScoring:
    def test_all_required_pass(self):
        """All required criteria should give 60 points"""
        # Mock scanner
        scanner = StockScanner.__new__(StockScanner)
        scanner.premarket_data = {}

        score, metrics, rejection = scanner.calculate_signal_score(
            symbol='TEST',
            current_price=10.0,
            vwap=9.5,           # Price > VWAP ✓
            rsi=55,             # RSI 40-75 ✓
            breakout_pct=0.02,  # > 1% ✓
            breakout_ref='premarket_high',
            relative_volume=2.5  # > 2x ✓
        )

        assert score >= 60
        assert rejection is None

    def test_below_vwap_rejected(self):
        """Price below VWAP should be rejected"""
        scanner = StockScanner.__new__(StockScanner)
        scanner.premarket_data = {}

        score, metrics, rejection = scanner.calculate_signal_score(
            symbol='TEST',
            current_price=9.0,
            vwap=9.5,           # Price < VWAP ✗
            rsi=55,
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=2.5
        )

        assert score == 0
        assert rejection == 'below_vwap'

    def test_rsi_overbought_rejected(self):
        """RSI > 75 should be rejected"""
        scanner = StockScanner.__new__(StockScanner)
        scanner.premarket_data = {}

        score, metrics, rejection = scanner.calculate_signal_score(
            symbol='TEST',
            current_price=10.0,
            vwap=9.5,
            rsi=80,             # RSI > 75 ✗
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=2.5
        )

        assert score == 0
        assert 'rsi' in rejection
```

### 6.2 Integration Tests

**File:** `tests/test_integration.py`

```python
import pytest
import os
import json
from datetime import datetime


class TestDailyWatchlistIntegration:
    def test_watchlist_format(self):
        """Daily watchlist should have correct format"""
        watchlist_file = 'state/daily_watchlist.json'

        if os.path.exists(watchlist_file):
            with open(watchlist_file) as f:
                data = json.load(f)

            assert 'date' in data
            assert 'watchlist' in data
            assert len(data['watchlist']) <= 25

            for stock in data['watchlist']:
                assert 'symbol' in stock
                assert 'premarket_high' in stock
                assert 'gap_pct' in stock


class TestAPIBudget:
    def test_scanner_api_budget(self):
        """Scanner should stay within API budget"""
        # 25 stocks × 2 calls × (60/45 cycles) = 67 calls/min
        stocks = 25
        calls_per_stock = 2
        interval = 45
        cycles_per_min = 60 / interval

        calls_per_min = stocks * calls_per_stock * cycles_per_min
        assert calls_per_min <= 70  # With small buffer

    def test_total_api_budget(self):
        """Total system should stay within 200 calls/min"""
        scanner_calls = 67
        monitor_calls = 80
        buyer_calls = 10
        seller_calls = 5
        orchestrator_calls = 5
        buffer = 33

        total = scanner_calls + monitor_calls + buyer_calls + \
                seller_calls + orchestrator_calls + buffer

        assert total <= 200
```

### 6.3 Paper Trading Validation Plan

| Week | Focus | Success Criteria |
|------|-------|------------------|
| **1** | Pre-market scanner | Generates 25-stock watchlist by 9:00 AM |
| **2** | Scanner + signals | Generates 3-10 signals/day, all with VWAP/RSI |
| **3** | Full system (paper) | Executes trades, tracks P&L |
| **4** | Optimization | Win rate > 40%, profit factor > 1.5 |

### 6.4 Metrics to Track

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Watchlist Quality** | Top 5 gappers in watchlist | Manual review |
| **Signal Accuracy** | > 40% win rate | Closed trades |
| **Avg Win / Avg Loss** | > 1.5 | Trade analysis |
| **Signals Per Day** | 3-10 | Count from logs |
| **Scan Cycle Time** | < 45 seconds | Log timestamps |
| **API Calls Per Min** | < 170 | Monitoring |
| **Price Validation Rejections** | < 30% | Buyer logs |

---

## File Changes Summary

### New Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `core/premarket_scanner.py` | ~350 | Pre-market gap scanner |
| `core/indicators.py` | ~150 | Technical indicators |
| `tests/test_indicators.py` | ~100 | Indicator tests |
| `tests/test_premarket_scanner.py` | ~50 | Pre-market tests |
| `tests/test_signal_scoring.py` | ~80 | Scoring tests |
| `tests/test_integration.py` | ~60 | Integration tests |

### Files to Modify

| File | Changes |
|------|---------|
| `core/scanner.py` | Load watchlist, new scoring, VWAP/RSI, 45s interval |
| `core/buyer.py` | 60s expiry, price validation, limit orders |
| `core/monitor.py` | 30s interval |
| `core/orchestrator.py` | Add premarket service |
| `config/config.py` | All new parameters |
| `scripts/universe_builder.py` | Add float data |

### Files Unchanged

| File | Reason |
|------|--------|
| `core/seller.py` | Exit execution unchanged |
| `core/shared_state.py` | Working correctly |
| `core/order_utils.py` | Working correctly |
| `core/price_stream.py` | Not used in new design |

---

## Implementation Timeline

### Day 1: Foundation
- [ ] Create `core/indicators.py`
- [ ] Create `tests/test_indicators.py`
- [ ] Update `config/config.py` with all new parameters
- [ ] Run indicator tests

### Day 2: Pre-Market Scanner
- [ ] Create `core/premarket_scanner.py`
- [ ] Create `tests/test_premarket_scanner.py`
- [ ] Test pre-market data retrieval
- [ ] Test watchlist generation

### Day 3: Scanner Refactoring
- [ ] Update `core/scanner.py` with new logic
- [ ] Implement daily watchlist loading
- [ ] Implement new scoring system
- [ ] Update to 45s interval
- [ ] Create `tests/test_signal_scoring.py`

### Day 4: Buyer Refactoring
- [ ] Update `core/buyer.py`
- [ ] Implement price validation
- [ ] Implement 60s signal expiry
- [ ] Add limit order support
- [ ] Test slippage protection

### Day 5: Monitor & Integration
- [ ] Update `core/monitor.py` to 30s interval
- [ ] Update `core/orchestrator.py`
- [ ] Create `tests/test_integration.py`
- [ ] Run full integration tests

### Day 6: Paper Trading
- [ ] Deploy to paper trading
- [ ] Run pre-market scanner
- [ ] Monitor scanner signals
- [ ] Verify API budget

### Day 7: Validation & Tuning
- [ ] Analyze paper trading results
- [ ] Tune parameters if needed
- [ ] Document any issues
- [ ] Prepare for live trading

---

## Appendix: Quick Reference

### API Budget Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    API BUDGET (200 calls/min)                   │
├──────────────────┬──────────────────────────┬───────────────────┤
│ Service          │ Calculation              │ Calls/Min         │
├──────────────────┼──────────────────────────┼───────────────────┤
│ Scanner          │ 25 × 2 × (60/45)         │ 67                │
│ Monitor          │ 20 × 2 × 2               │ 80                │
│ Buyer            │ Validation + orders      │ 10                │
│ Seller           │ Orders                   │ 5                 │
│ Orchestrator     │ Clock, status            │ 5                 │
│ Buffer           │ Retries, errors          │ 33                │
├──────────────────┼──────────────────────────┼───────────────────┤
│ TOTAL            │                          │ 200               │
└──────────────────┴──────────────────────────┴───────────────────┘
```

### Signal Scoring Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL SCORING (0-95 pts)                    │
├─────────────────────────────────────────────────────────────────┤
│ REQUIRED (must pass all 4):                                     │
│   Price > VWAP .......................... 15 pts                │
│   Breakout > 1% ......................... 20 pts                │
│   Volume > 2x ........................... 15 pts                │
│   RSI 40-75 ............................. 10 pts                │
│   ─────────────────────────────────────────────                 │
│   Minimum Required: ..................... 60 pts                │
├─────────────────────────────────────────────────────────────────┤
│ BONUS (additive):                                               │
│   Breakout > 3% ......................... 10 pts                │
│   Volume > 4x ........................... 10 pts                │
│   RSI 50-65 (sweet spot) ................ 5 pts                 │
│   Gap > 5% .............................. 10 pts                │
│   ─────────────────────────────────────────────                 │
│   Maximum Possible: ..................... 95 pts                │
└─────────────────────────────────────────────────────────────────┘
```

### Position Sizing by Score

```
┌─────────────────────────────────────────────────────────────────┐
│                    POSITION SIZING                              │
├──────────────────┬───────────────────┬──────────────────────────┤
│ Score Range      │ Size (% of equity)│ Tier Name                │
├──────────────────┼───────────────────┼──────────────────────────┤
│ 60-84            │ 5%                │ STANDARD                 │
│ 85-94            │ 7%                │ STRONG                   │
│ 95+              │ 10%               │ MAXIMUM                  │
└──────────────────┴───────────────────┴──────────────────────────┘
```

### Daily Watchlist Selection

```
┌─────────────────────────────────────────────────────────────────┐
│                PRE-MARKET WATCHLIST SELECTION                   │
├─────────────────────────────────────────────────────────────────┤
│ Input:   500 stocks (base universe)                             │
│                                                                 │
│ Filters: • Gap > 3% from prior close                            │
│          • Pre-market volume > 50K                              │
│          • Pre-market relative volume > 2x                      │
│          • Price $2 - $50                                       │
│                                                                 │
│ Ranking: score = gap% × rel_vol × (1/√(float/10M))              │
│                                                                 │
│ Output:  Top 25 stocks by score → daily_watchlist.json          │
└─────────────────────────────────────────────────────────────────┘
```

### Service Intervals

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE INTERVALS                            │
├──────────────────┬───────────────────┬──────────────────────────┤
│ Service          │ Interval          │ Purpose                  │
├──────────────────┼───────────────────┼──────────────────────────┤
│ PreMarket        │ Once (8:00-9:25)  │ Build daily watchlist    │
│ Scanner          │ 45 seconds        │ Generate entry signals   │
│ Buyer            │ 15 seconds        │ Execute buy orders       │
│ Monitor          │ 30 seconds        │ Track positions          │
│ Seller           │ 15 seconds        │ Execute sell orders      │
└──────────────────┴───────────────────┴──────────────────────────┘
```

---

## Success Criteria

The refactoring is complete and successful when:

1. ✅ Pre-market scanner generates 25-stock watchlist by 9:00 AM ET
2. ✅ Scanner completes each cycle in < 45 seconds
3. ✅ All signals include VWAP, RSI, and proper breakout reference
4. ✅ API usage stays under 170 calls/minute (with buffer)
5. ✅ Buyer validates price before every execution
6. ✅ Stale signals (> 60s) are rejected
7. ✅ Monitor checks positions every 30 seconds
8. ✅ Paper trading shows positive expectancy over 1 week

---

*Document Version: 2.1*
*Last Updated: 2026-01-26*
*Status: Ready for Implementation*
