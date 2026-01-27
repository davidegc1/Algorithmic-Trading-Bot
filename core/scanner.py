"""
SCANNER SERVICE v2.1
Scans daily watchlist (25 stocks) for buy signals using VWAP, RSI, and proper breakout detection

Key Changes from v1:
- Loads daily watchlist (25 stocks) from premarket scanner
- Uses VWAP and RSI indicators (industry standard)
- Breakout from premarket high (not candle low)
- 45-second scan interval (optimized for API budget)
- New scoring system: 60 base (required) + 35 bonus

API Budget: 25 stocks × 2 calls × 1.33 cycles/min = 67 calls/min
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# Eastern timezone for market hours
ET = ZoneInfo("America/New_York")

from core.shared_state import get_state_dir, get_logs_dir, SafeJSONFile, SignalNotifier
from core.indicators import TechnicalIndicators
from config.config import (
    # Scanning
    SCAN_INTERVAL_SECONDS,
    UNIVERSE_PATH,
    BARS_FAST,
    BARS_PRIMARY,
    TIMEFRAME_FAST,
    TIMEFRAME_PRIMARY,
    # Signal Generation
    REQUIRE_ABOVE_VWAP,
    MIN_BREAKOUT_PCT,
    MIN_RELATIVE_VOLUME,
    RSI_MIN,
    RSI_MAX,
    MIN_ENTRY_SCORE,
    # Scoring
    SCORE_ABOVE_VWAP,
    SCORE_BREAKOUT,
    SCORE_VOLUME,
    SCORE_RSI_VALID,
    SCORE_STRONG_BREAKOUT,
    SCORE_HIGH_VOLUME,
    SCORE_RSI_SWEET,
    SCORE_LARGE_GAP,
    # Buyer settings for hot signals
    HOT_SIGNAL_MIN_SCORE,
    # Default universe
    DEFAULT_UNIVERSE,
)

load_dotenv()

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'scanner.log'), mode='a'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SignalScanner:
    """
    Scans daily watchlist for high-quality entry signals using VWAP, RSI, and volume

    v2.1 Changes:
    - Loads 25-stock daily watchlist from premarket scanner
    - Uses VWAP and RSI from indicators module
    - Proper breakout detection from premarket high
    - 45-second scan interval
    - New 60-point base + 35-point bonus scoring
    """

    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

        self.api = tradeapi.REST(
            self.api_key,
            self.api_secret,
            self.base_url,
            api_version='v2'
        )

        # Strategy parameters from config
        self.MIN_ENTRY_SCORE = MIN_ENTRY_SCORE
        self.MIN_BREAKOUT_PCT = MIN_BREAKOUT_PCT
        self.MIN_RELATIVE_VOLUME = MIN_RELATIVE_VOLUME
        self.RSI_MIN = RSI_MIN
        self.RSI_MAX = RSI_MAX

        # Universe and premarket data
        self.universe = []
        self.premarket_data = {}  # symbol -> {prior_close, premarket_high, gap_pct, ...}

        # File paths
        state_dir = get_state_dir()
        self.signals_file = os.path.join(state_dir, 'signals.json')
        self.watchlist_file = os.path.join(state_dir, 'daily_watchlist.json')

        # Hot signal notifier for fast-path execution
        self.signal_notifier = SignalNotifier()

        logger.info("Scanner v2.1 initialized")
        logger.info(f"  Min Entry Score: {self.MIN_ENTRY_SCORE}")
        logger.info(f"  Min Breakout: {self.MIN_BREAKOUT_PCT*100}%")
        logger.info(f"  Min Relative Volume: {self.MIN_RELATIVE_VOLUME}x")
        logger.info(f"  RSI Range: {self.RSI_MIN}-{self.RSI_MAX}")

    def load_universe(self) -> List[str]:
        """
        Load today's watchlist (25 stocks) or fall back to base universe

        Priority:
        1. Daily watchlist (if exists and from today)
        2. Universe file (limited to 25 stocks)
        3. Default universe
        """
        # Try to load today's watchlist
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r') as f:
                    data = json.load(f)

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
                    logger.warning(f"Watchlist is from {watchlist_date}, not today ({today})")

            except Exception as e:
                logger.error(f"Error loading watchlist: {e}")

        # Fallback to universe file
        logger.warning("⚠️ No daily watchlist - using fallback universe (limited to 25)")

        if os.path.exists(UNIVERSE_PATH):
            try:
                with open(UNIVERSE_PATH, 'r') as f:
                    all_stocks = [line.strip() for line in f if line.strip()]
                self.universe = all_stocks[:25]  # LIMIT TO 25
                logger.info(f"📋 Loaded {len(self.universe)} stocks from {UNIVERSE_PATH}")
            except Exception as e:
                logger.error(f"Error loading universe file: {e}")
                self.universe = DEFAULT_UNIVERSE[:25]
        else:
            self.universe = DEFAULT_UNIVERSE[:25]
            logger.info(f"📋 Using DEFAULT_UNIVERSE: {len(self.universe)} stocks")

        self.premarket_data = {}
        return self.universe

    def get_historical_bars(self, symbol: str, timeframe: str, limit: int = 50) -> pd.DataFrame:
        """Get historical price data with error handling"""
        try:
            bars = self.api.get_bars(
                symbol,
                timeframe,
                limit=limit
            ).df

            if bars.empty:
                return pd.DataFrame()

            if not isinstance(bars.index, pd.DatetimeIndex):
                bars.index = pd.to_datetime(bars.index)

            return bars

        except Exception as e:
            logger.debug(f"Error getting bars for {symbol}: {e}")
            return pd.DataFrame()

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
        2. Session high (current day's bars)
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
                # Only use if price is making new highs
                if current_price >= session_high * 0.99:  # Within 1% of high
                    breakout_pct = (current_price - session_high) / session_high
                    return breakout_pct, 'session_high'

        # 3. Prior close (gap reference)
        if symbol in self.premarket_data:
            prior_close = self.premarket_data[symbol].get('prior_close')
            if prior_close and prior_close > 0:
                breakout_pct = (current_price - prior_close) / prior_close
                return breakout_pct, 'prior_close'

        # 4. Fallback: Use lowest low of session as reference
        if not bars_5min.empty:
            session_low = float(bars_5min['low'].min())
            if session_low > 0:
                breakout_pct = (current_price - session_low) / session_low
                return breakout_pct, 'session_low'

        return 0.0, 'none'

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
        if REQUIRE_ABOVE_VWAP and current_price <= vwap:
            return 0, {'vwap': round(vwap, 4)}, 'below_vwap'

        score += SCORE_ABOVE_VWAP
        metrics['vwap'] = round(vwap, 4)
        metrics['price_vs_vwap_pct'] = round((current_price / vwap - 1) * 100, 2)

        # 2. Breakout > 1% (REQUIRED - 20 pts)
        if breakout_pct < self.MIN_BREAKOUT_PCT:
            return 0, metrics, f'breakout_{breakout_pct*100:.1f}%_below_{self.MIN_BREAKOUT_PCT*100}%'

        score += SCORE_BREAKOUT
        metrics['breakout_pct'] = round(breakout_pct * 100, 2)
        metrics['breakout_ref'] = breakout_ref

        # 3. Relative Volume > 2x (REQUIRED - 15 pts)
        if relative_volume < self.MIN_RELATIVE_VOLUME:
            return 0, metrics, f'volume_{relative_volume:.1f}x_below_{self.MIN_RELATIVE_VOLUME}x'

        score += SCORE_VOLUME
        metrics['relative_volume'] = round(relative_volume, 2)

        # 4. RSI 40-75 (REQUIRED - 10 pts)
        if not TechnicalIndicators.is_rsi_valid(rsi, self.RSI_MIN, self.RSI_MAX):
            return 0, metrics, f'rsi_{rsi:.0f}_outside_{self.RSI_MIN}-{self.RSI_MAX}'

        score += SCORE_RSI_VALID
        metrics['rsi'] = round(rsi, 1)

        # Base score: 60 (all required criteria passed)

        # ==================== BONUS CHECKS ====================

        # 5. Breakout > 3% (BONUS - 10 pts)
        if breakout_pct >= 0.03:
            score += SCORE_STRONG_BREAKOUT
            metrics['strong_breakout'] = True

        # 6. Volume > 4x (BONUS - 10 pts)
        if relative_volume >= 4.0:
            score += SCORE_HIGH_VOLUME
            metrics['high_volume'] = True

        # 7. RSI sweet spot 50-65 (BONUS - 5 pts)
        if TechnicalIndicators.is_rsi_sweet_spot(rsi):
            score += SCORE_RSI_SWEET
            metrics['rsi_sweet_spot'] = True

        # 8. Gap > 5% (BONUS - 10 pts)
        if symbol in self.premarket_data:
            gap_pct = self.premarket_data[symbol].get('gap_pct', 0)
            metrics['gap_pct'] = round(gap_pct * 100, 2)
            if gap_pct >= 0.05:
                score += SCORE_LARGE_GAP
                metrics['large_gap'] = True

        return score, metrics, None

    def scan_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Scan a single symbol with new technical analysis

        API Calls: 2 per stock (5min bars + 2min bars)
        """
        try:
            # 1. Get bars (OPTIMIZED: only 2 timeframes)
            bars_5min = self.get_historical_bars(symbol, TIMEFRAME_PRIMARY, limit=BARS_PRIMARY)
            bars_2min = self.get_historical_bars(symbol, TIMEFRAME_FAST, limit=BARS_FAST)

            if bars_5min.empty or len(bars_5min) < 14:  # Need 14 for RSI
                logger.debug(f"{symbol}: Insufficient bar data")
                return None

            # 2. Extract current values
            current_price = float(bars_5min.iloc[-1]['close'])
            current_volume = int(bars_5min.iloc[-1]['volume'])

            # 3. Calculate VWAP
            vwap_series = TechnicalIndicators.calculate_vwap(bars_5min)
            vwap = float(vwap_series.iloc[-1]) if not vwap_series.empty else current_price

            # 4. Calculate RSI
            rsi_series = TechnicalIndicators.calculate_rsi(bars_5min['close'], period=14)
            rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

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
            if score < self.MIN_ENTRY_SCORE:
                logger.debug(f"{symbol} score {score} below minimum {self.MIN_ENTRY_SCORE}")
                return None

            # 10. Calculate velocity and acceleration for additional context
            velocity = TechnicalIndicators.calculate_velocity(bars_5min, periods=5)
            acceleration = TechnicalIndicators.calculate_acceleration(bars_5min, velocity_period=5)

            # 11. Build signal
            signal = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price': round(current_price, 4),
                'score': score,
                'velocity': round(velocity * 100, 4),  # as percentage
                'acceleration': round(acceleration, 2),
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

    def scan_universe(self) -> List[Dict]:
        """
        Scan daily watchlist (25 stocks) for signals

        Returns:
            List of valid signals, sorted by score descending
        """
        logger.info("=" * 80)
        logger.info(f"SCANNING {len(self.universe)} STOCKS FOR SIGNALS")
        logger.info(f"   Min Score: {self.MIN_ENTRY_SCORE}")
        logger.info(f"   Required: VWAP + {self.MIN_BREAKOUT_PCT*100}% breakout + {self.MIN_RELATIVE_VOLUME}x vol + RSI {self.RSI_MIN}-{self.RSI_MAX}")
        logger.info("=" * 80)

        signals = []

        for i, symbol in enumerate(self.universe, 1):
            logger.debug(f"[{i}/{len(self.universe)}] Scanning {symbol}...")

            signal = self.scan_symbol(symbol)
            if signal:
                signals.append(signal)

            # Rate limiting: 25 stocks × 2 calls = 50 calls per cycle
            # At 45s interval = 67 calls/min, well under 200/min limit
            time.sleep(0.2)  # 200ms delay between stocks

        # Sort by score (highest first)
        signals.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Scan complete: Found {len(signals)} valid signals")

        return signals

    def save_signals(self, signals: List[Dict]):
        """Save signals to JSON file and notify hot signals"""
        try:
            with SafeJSONFile(self.signals_file, 'w') as file_data:
                file_data['timestamp'] = datetime.now().isoformat()
                file_data['scan_version'] = '2.1'
                file_data['signals'] = signals

            logger.info(f"💾 Saved {len(signals)} signals to {self.signals_file}")

            # Check for hot signals (score >= 90) and notify for fast-path
            for signal in signals:
                if signal.get('score', 0) >= HOT_SIGNAL_MIN_SCORE:
                    self.signal_notifier.notify_hot_signal(signal)
                    logger.info(f"🔥 HOT SIGNAL: {signal['symbol']} score={signal['score']}")
                    break  # Only one hot signal at a time

        except Exception as e:
            logger.error(f"Error saving signals: {e}")

    def run_once(self):
        """Run one scan cycle"""
        try:
            # Load universe/watchlist
            self.load_universe()

            # Scan for signals
            signals = self.scan_universe()

            # Save signals
            self.save_signals(signals)

            logger.info(f"📊 Scan cycle complete at {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            logger.error(f"Error in scan cycle: {e}")

    def run_continuous(self, interval_seconds: int = None):
        """
        Run scanner continuously with 45-second intervals

        API Budget:
        - 25 stocks × 2 calls = 50 calls per cycle
        - At 45s interval = 67 calls/minute
        - Well within 200/min limit
        """
        if interval_seconds is None:
            interval_seconds = SCAN_INTERVAL_SECONDS

        logger.info("=" * 80)
        logger.info("🚀 SCANNER SERVICE v2.1 STARTING")
        logger.info(f"   Scan Interval: {interval_seconds}s")
        logger.info(f"   Expected Stocks: 25 (daily watchlist)")
        logger.info(f"   API Calls/Cycle: ~50")
        logger.info(f"   Est. Calls/Min: ~{50 * (60/interval_seconds):.0f}")
        logger.info("=" * 80)

        try:
            while True:
                try:
                    # Check if market is open
                    clock = self.api.get_clock()

                    if clock.is_open:
                        cycle_start = time.time()

                        # Run scan
                        self.run_once()

                        cycle_duration = time.time() - cycle_start
                        logger.info(
                            f"⏱️  Cycle: {cycle_duration:.1f}s | "
                            f"Next scan in {interval_seconds}s"
                        )

                        # Wait for next cycle
                        sleep_time = max(0, interval_seconds - cycle_duration)
                        time.sleep(sleep_time)

                    else:
                        logger.info(f"🌙 Market closed. Next open: {clock.next_open}")
                        time.sleep(300)  # 5 min sleep when market closed

                except Exception as e:
                    logger.error(f"Scan cycle error: {e}")
                    time.sleep(60)

        except KeyboardInterrupt:
            logger.info("⚠️ Scanner stopped by user")


def main():
    """Entry point"""
    scanner = SignalScanner()
    scanner.run_continuous()


if __name__ == "__main__":
    main()
