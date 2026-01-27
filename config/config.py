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

# Universe file path (fallback if no daily watchlist)
UNIVERSE_PATH = 'universes/base_universe/base_universe.txt'

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

# Scoring points - REQUIRED criteria (60 points total)
SCORE_ABOVE_VWAP = 15              # Required: price > VWAP
SCORE_BREAKOUT = 20                # Required: breakout > 1%
SCORE_VOLUME = 15                  # Required: volume > 2x
SCORE_RSI_VALID = 10               # Required: RSI 40-75

# Scoring points - BONUS criteria (up to 35 additional points)
SCORE_STRONG_BREAKOUT = 10         # Bonus: breakout > 3%
SCORE_HIGH_VOLUME = 10             # Bonus: volume > 4x
SCORE_RSI_SWEET = 5                # Bonus: RSI 50-65
SCORE_LARGE_GAP = 10               # Bonus: gap > 5%

# Legacy scoring (kept for compatibility, will be deprecated)
SCORE_5MIN_BREAKOUT = 25           # Points for 5-min breakout (REQUIRED)
SCORE_15MIN_GREEN = 10             # Points for 15-min green (REQUIRED)
SCORE_2MIN_BREAKOUT = 15           # Bonus points for 2-min breakout
SCORE_VELOCITY_RATIO = 15          # Bonus points for V1 > V2
SCORE_ACCELERATION = 15            # Bonus points for A > 1.2
SCORE_ACCELERATION_MED = 10        # Points for A > 1.0 but < 1.2

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
POSITION_SIZE_PYRAMID = 0.025      # 2.5% when adding to winners

SCORE_TIER_STANDARD = (60, 84)     # Standard tier
SCORE_TIER_STRONG = (85, 94)       # Strong tier
SCORE_TIER_MAXIMUM = (95, 100)     # Maximum tier

# ============================================================================
# RISK MANAGEMENT (unchanged)
# ============================================================================
STOP_LOSS_PCT = 0.025              # 2.5% hard stop loss
BREAKEVEN_PROFIT = 0.05            # Move stop to breakeven at +5%
QUICK_LOCK_PROFIT = 0.02           # Lock +2% profit once at +5%
TRAIL_RULE_MULTIPLIER = 0.1        # 10% of profit level = trail percentage

# Trailing stops by profit tier
TRAILING_STOPS = {
    0.05: 0.02,    # +5% profit -> 2% trailing stop
    0.10: 0.03,    # +10% profit -> 3% trailing stop
    0.15: 0.04,    # +15% profit -> 4% trailing stop
    0.20: 0.05,    # +20% profit -> 5% trailing stop
    0.30: 0.07,    # +30% profit -> 7% trailing stop
    0.50: 0.10,    # +50% profit -> 10% trailing stop
    1.00: 0.15,    # +100% profit -> 15% trailing stop
}

# Deceleration exit
DECEL_EXIT_THRESHOLD = 0.5         # Exit if acceleration drops below 0.5
DECEL_TIGHTEN_THRESHOLD = 0.8      # Tighten stop if A < 0.8
MIN_PROFIT_FOR_DECEL_CHECK = 0.05  # Only check decel if +5% profit

# ============================================================================
# MONITOR SETTINGS (UPDATED)
# ============================================================================
MONITOR_INTERVAL_SECONDS = 30      # Check positions every 30s (was 60)
POSITION_CHECK_INTERVAL = 10       # Legacy: Check positions every 10 seconds

# ============================================================================
# SELLER SETTINGS (unchanged)
# ============================================================================
SELLER_INTERVAL_SECONDS = 15       # Check for sell signals every 15s

# ============================================================================
# COOLDOWN (unchanged)
# ============================================================================
COOLDOWN_MINUTES = 15              # Wait 15 min after selling before re-buying

# ============================================================================
# RE-ENTRY & PYRAMIDING RULES
# ============================================================================
ALLOW_PYRAMIDING = True            # Allow adding to winning positions
MIN_PROFIT_FOR_PYRAMID = 0.10      # Must have 10% profit to add
MIN_SCORE_IMPROVEMENT = 5          # New signal must be 5+ points higher
PYRAMID_SIZE_PCT = 0.025           # Use smaller size when pyramiding (2.5%)

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
# VOLATILITY FILTERS
# ============================================================================
MIN_ATR_PCT = 0.05                 # 5% daily ATR minimum
HIGH_VOLATILITY_ATR = 0.10         # 10% for extreme volatility

# ============================================================================
# ENTRY REQUIREMENTS (legacy, kept for compatibility)
# ============================================================================
BREAKOUT_5MIN_PCT = 0.03           # 3% breakout on 5-min chart
BREAKOUT_2MIN_PCT = 0.025          # 2.5% breakout on 2-min chart (bonus)
VOLUME_RATIO_MIN = 2.0             # 2x average volume (REQUIRED)
ACCELERATION_MIN = 1.2             # Acceleration threshold (BONUS)

# ============================================================================
# DEFAULT WATCHLIST (if no universe file provided)
# ============================================================================
# Updated to remove dead tickers (ZYXI, IRBT)
DEFAULT_UNIVERSE = [
    "CAPR", "AHMA", "PLRZ", "CETX", "KTTA", "NCPL", "MNDR", "KITT", "CETY",
    "EPSM", "CMCT", "BEAT", "WHLR", "SGBX", "AEHL", "RZLT", "CYPH", "LFS",
    "MIGI", "EB", "QTTB", "RUBI", "SEMR"
]

# ============================================================================
# LOGGING - CLEAN OUTPUT
# ============================================================================
LOG_LEVEL = 'INFO'                 # Standard log level
LOG_FILE = 'trading_bot.log'       # Detailed log file
LOG_FILE_DETAILED = 'trading_bot_detailed.log'  # Everything
LOG_TO_CONSOLE = True              # Show important events on console
CONSOLE_LOG_LEVEL = 'TRADE'        # Console shows: SCAN, SIGNAL, TRADE, ERROR

# ============================================================================
# ALPACA API
# ============================================================================
PAPER_TRADING = True               # Use paper trading by default
API_VERSION = 'v2'

# ============================================================================
# BACKTESTING (for future use)
# ============================================================================
BACKTEST_START_DATE = '2024-01-01'
BACKTEST_END_DATE = '2024-12-31'
BACKTEST_INITIAL_CAPITAL = 10000

# ============================================================================
# API BUDGET SUMMARY
# ============================================================================
"""
Service         | Calculation                           | Calls/Min
----------------|---------------------------------------|----------
Scanner         | 25 stocks x 2 calls x (60/45)         | 67
Monitor         | 20 positions x 2 calls x 2            | 80
Buyer           | Price validation + orders             | 10
Seller          | Order execution                       | 5
Orchestrator    | Clock, status                         | 5
Buffer          | Retries, errors                       | 33
----------------|---------------------------------------|----------
TOTAL           |                                       | 200
"""
