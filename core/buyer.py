"""
BUYER SERVICE v2.1
Executes buy orders with price validation and slippage protection

Key Changes from v1:
- 60-second signal expiry (was 5 minutes)
- Price validation before execution (2% max slippage)
- Spread check (2% max spread)
- Limit orders with 0.5% buffer (optional)
- Hot signal fast-path execution

API Budget: ~10 calls/min (price validation + orders)
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

from core.shared_state import (
    CooldownManager, PositionManager, get_state_dir, get_logs_dir,
    SafeJSONFile, SignalNotifier
)
from core.order_utils import OrderExecutor
from config.config import (
    # Position sizing
    MAX_POSITIONS,
    POSITION_SIZE_STANDARD,
    POSITION_SIZE_STRONG,
    POSITION_SIZE_MAXIMUM,
    SCORE_TIER_STANDARD,
    SCORE_TIER_STRONG,
    SCORE_TIER_MAXIMUM,
    # Risk management
    STOP_LOSS_PCT,
    COOLDOWN_MINUTES,
    # Buyer settings (NEW)
    SIGNAL_MAX_AGE_SECONDS,
    MAX_SLIPPAGE_PCT,
    MAX_SPREAD_PCT,
    USE_LIMIT_ORDERS,
    LIMIT_ORDER_BUFFER,
    HOT_SIGNAL_MIN_SCORE,
    HOT_CHECK_INTERVAL,
)

load_dotenv()

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'buyer.log'), mode='a'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OrderBuyer:
    """
    Executes buy orders with price validation and slippage protection

    v2.1 Changes:
    - 60-second signal expiry (prevents stale entries)
    - Price validation (max 2% slippage from signal price)
    - Spread check (max 2% bid-ask spread)
    - Optional limit orders with buffer
    - Hot signal fast-path for scores >= 90
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

        # Order executor with proper polling
        self.order_executor = OrderExecutor(self.api)

        # Position management from config
        self.MAX_POSITIONS = MAX_POSITIONS
        self.STOP_LOSS_PCT = STOP_LOSS_PCT

        # Price validation settings from config
        self.SIGNAL_MAX_AGE_SECONDS = SIGNAL_MAX_AGE_SECONDS
        self.MAX_SLIPPAGE_PCT = MAX_SLIPPAGE_PCT
        self.MAX_SPREAD_PCT = MAX_SPREAD_PCT
        self.USE_LIMIT_ORDERS = USE_LIMIT_ORDERS
        self.LIMIT_ORDER_BUFFER = LIMIT_ORDER_BUFFER

        # State managers
        state_dir = get_state_dir()
        self.cooldown_manager = CooldownManager(
            cooldowns_file=os.path.join(state_dir, 'cooldowns.json'),
            cooldown_minutes=COOLDOWN_MINUTES
        )

        self.position_manager = PositionManager(
            positions_file=os.path.join(state_dir, 'positions.json')
        )

        self.signals_file = os.path.join(state_dir, 'signals.json')

        # Hot signal notifier for fast-path execution
        self.signal_notifier = SignalNotifier()

        # Load and reconcile state on startup
        self.load_state()

        logger.info("Buyer v2.1 initialized")
        logger.info(f"  Signal Max Age: {self.SIGNAL_MAX_AGE_SECONDS}s")
        logger.info(f"  Max Slippage: {self.MAX_SLIPPAGE_PCT*100}%")
        logger.info(f"  Max Spread: {self.MAX_SPREAD_PCT*100}%")
        logger.info(f"  Use Limit Orders: {self.USE_LIMIT_ORDERS}")

    def load_signals(self) -> List[Dict]:
        """
        Load fresh signals from scanner (max 60 seconds old)

        Returns:
            List of fresh signals, sorted by score descending
        """
        try:
            with SafeJSONFile(self.signals_file, 'r') as data:
                signals = data.get('signals', [])

                # Filter out stale signals (using config value, default 60s)
                fresh_signals = []
                cutoff = datetime.now() - timedelta(seconds=self.SIGNAL_MAX_AGE_SECONDS)

                for signal in signals:
                    try:
                        signal_time = datetime.fromisoformat(signal['timestamp'])
                        if signal_time >= cutoff:
                            fresh_signals.append(signal)
                        else:
                            age = (datetime.now() - signal_time).total_seconds()
                            logger.debug(f"{signal['symbol']} signal expired ({age:.0f}s old)")
                    except (KeyError, ValueError) as e:
                        logger.debug(f"Invalid signal timestamp: {e}")

                if fresh_signals:
                    logger.info(f"📥 Loaded {len(fresh_signals)} fresh signals (max {self.SIGNAL_MAX_AGE_SECONDS}s old)")
                else:
                    logger.debug("No fresh signals available")

                return fresh_signals

        except FileNotFoundError:
            logger.debug("No signals file found")
            return []
        except Exception as e:
            logger.error(f"Error loading signals: {e}")
            return []

    def validate_price(self, symbol: str, signal_price: float) -> Tuple[bool, float, str]:
        """
        Validate current price against signal price (slippage protection)

        Args:
            symbol: Stock symbol
            signal_price: Price at signal generation

        Returns:
            (is_valid, current_price, reason)
        """
        try:
            # Get latest quote
            quote = self.api.get_latest_quote(symbol)

            bid = float(quote.bid_price) if quote.bid_price else 0
            ask = float(quote.ask_price) if quote.ask_price else 0

            if bid <= 0 or ask <= 0:
                return False, 0, "invalid_quote"

            # Calculate mid price and spread
            mid_price = (bid + ask) / 2
            spread_pct = (ask - bid) / mid_price

            # Check spread
            if spread_pct > self.MAX_SPREAD_PCT:
                logger.warning(f"{symbol} spread too wide: {spread_pct*100:.2f}% > {self.MAX_SPREAD_PCT*100}%")
                return False, mid_price, f"spread_{spread_pct*100:.1f}%"

            # Check slippage from signal price
            slippage_pct = (mid_price - signal_price) / signal_price

            if slippage_pct > self.MAX_SLIPPAGE_PCT:
                logger.warning(f"{symbol} price moved too much: ${signal_price:.2f} -> ${mid_price:.2f} ({slippage_pct*100:.1f}%)")
                return False, mid_price, f"slippage_{slippage_pct*100:.1f}%"

            # Price is valid
            logger.debug(f"{symbol} price validated: ${signal_price:.2f} -> ${mid_price:.2f} ({slippage_pct*100:+.1f}%)")
            return True, mid_price, "ok"

        except Exception as e:
            logger.error(f"Error validating price for {symbol}: {e}")
            return False, 0, f"error_{str(e)[:20]}"

    def get_current_positions(self) -> Dict[str, Dict]:
        """Get current positions from Alpaca"""
        try:
            positions = {}
            alpaca_positions = self.api.list_positions()

            for pos in alpaca_positions:
                positions[pos.symbol] = {
                    'qty': int(pos.qty),
                    'entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc)
                }

            logger.debug(f"Current positions: {len(positions)}/{self.MAX_POSITIONS}")
            return positions

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}

    def load_state(self):
        """Load and reconcile state on startup"""
        try:
            logger.info("🔄 Loading state on startup...")

            # Get current positions from Alpaca
            alpaca_positions = self.get_current_positions()

            # Convert to format expected by reconcile
            alpaca_pos_dict = {}
            for symbol, pos_info in alpaca_positions.items():
                alpaca_pos_dict[symbol] = {
                    'qty': pos_info['qty'],
                    'entry_price': pos_info['entry_price'],
                    'avg_entry_price': pos_info['entry_price'],
                    'current_price': pos_info['current_price']
                }

            # Reconcile positions with Alpaca
            self.position_manager.reconcile_with_alpaca(alpaca_pos_dict)

            logger.info("✅ State loaded and reconciled")

        except Exception as e:
            logger.error(f"Error loading state: {e}")

    def check_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown (True = can trade)"""
        if self.cooldown_manager.is_in_cooldown(symbol):
            cooldown_until = self.cooldown_manager.get_cooldown_until(symbol)
            if cooldown_until:
                remaining = (cooldown_until - datetime.now()).total_seconds() / 60
                logger.info(f"⏸️ {symbol} in cooldown - {remaining:.1f} min remaining (until {cooldown_until.strftime('%H:%M:%S')})")
            return False
        return True

    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power)
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {}

    def get_position_size_pct(self, score: int) -> float:
        """
        Get position size percentage based on signal score tier

        Tiers (from config):
        - Standard (60-84): 5%
        - Strong (85-94): 7%
        - Maximum (95+): 10%
        """
        if SCORE_TIER_MAXIMUM[0] <= score <= SCORE_TIER_MAXIMUM[1]:
            return POSITION_SIZE_MAXIMUM  # 10%
        elif SCORE_TIER_STRONG[0] <= score <= SCORE_TIER_STRONG[1]:
            return POSITION_SIZE_STRONG   # 7%
        else:
            return POSITION_SIZE_STANDARD # 5%

    def execute_buy(self, signal: Dict, validated_price: float = None) -> bool:
        """
        Execute buy order for signal with price validation

        Args:
            signal: Signal dict from scanner
            validated_price: Pre-validated current price (optional)

        Returns:
            True if successful, False otherwise
        """
        symbol = signal['symbol']
        score = signal.get('score', 60)
        signal_price = signal['price']

        try:
            # Price validation (if not already done)
            if validated_price is None:
                is_valid, current_price, reason = self.validate_price(symbol, signal_price)
                if not is_valid:
                    logger.warning(f"❌ {symbol} price validation failed: {reason}")
                    return False
            else:
                current_price = validated_price

            # Get account info
            account = self.get_account_info()
            if not account:
                return False

            # Calculate position size based on signal score tier
            portfolio_value = account['equity']
            position_size_pct = self.get_position_size_pct(score)
            position_value = portfolio_value * position_size_pct
            quantity = int(position_value / current_price)

            if quantity <= 0:
                logger.warning(f"{symbol} quantity is 0")
                return False

            # Determine order type and price
            tier_name = "MAX" if position_size_pct >= 0.10 else "STRONG" if position_size_pct >= 0.07 else "STD"

            if self.USE_LIMIT_ORDERS:
                # Limit order with buffer above current price
                limit_price = round(current_price * (1 + self.LIMIT_ORDER_BUFFER), 2)
                logger.info(f"🔵 BUYING {symbol} - Score: {score} ({tier_name})")
                logger.info(f"   Signal: ${signal_price:.2f} -> Current: ${current_price:.2f}")
                logger.info(f"   Limit: ${limit_price:.2f}, Qty: {quantity}, Size: {position_size_pct*100:.0f}%")

                # Submit limit order
                success, result = self.order_executor.submit_and_wait(
                    symbol=symbol,
                    qty=quantity,
                    side='buy',
                    order_type='limit',
                    limit_price=limit_price
                )
            else:
                # Market order
                logger.info(f"🔵 BUYING {symbol} - Score: {score} ({tier_name})")
                logger.info(f"   Signal: ${signal_price:.2f} -> Current: ${current_price:.2f}")
                logger.info(f"   Qty: {quantity}, Size: {position_size_pct*100:.0f}%")

                success, result = self.order_executor.submit_and_wait(
                    symbol=symbol,
                    qty=quantity,
                    side='buy'
                )

            if success:
                filled_price = result['filled_price']
                filled_qty = result.get('filled_qty', quantity)
                stop_price = filled_price * (1 - self.STOP_LOSS_PCT)

                logger.info(f"✅ FILLED {symbol} @ ${filled_price:.2f}")
                logger.info(f"   Stop Loss: ${stop_price:.2f} ({self.STOP_LOSS_PCT*100}%)")

                # Save position info for monitor
                self.save_position_info(symbol, {
                    'entry_price': filled_price,
                    'quantity': filled_qty,
                    'entry_time': datetime.now().isoformat(),
                    'stop_loss': stop_price,
                    'signal_score': score,
                    'signal_price': signal_price,
                    'slippage_pct': (filled_price - signal_price) / signal_price,
                    # Preserve signal metadata
                    'vwap': signal.get('vwap'),
                    'rsi': signal.get('rsi'),
                    'breakout_pct': signal.get('breakout_pct'),
                    'relative_volume': signal.get('relative_volume'),
                })

                return True
            else:
                reason = result.get('reason', result.get('status', 'unknown'))
                logger.warning(f"❌ {symbol} order not filled: {reason}")
                return False

        except Exception as e:
            logger.error(f"Error buying {symbol}: {e}")
            return False

    def save_position_info(self, symbol: str, info: Dict):
        """Save position info using shared position manager"""
        self.position_manager.add_position(symbol, info)

    def process_signals(self):
        """Process signals with price validation and execute buys"""
        try:
            # Load fresh signals
            signals = self.load_signals()
            if not signals:
                logger.debug("No signals to process")
                return

            # Get current positions
            positions = self.get_current_positions()

            # Check available slots
            available_slots = self.MAX_POSITIONS - len(positions)
            if available_slots <= 0:
                logger.info(f"⚠️ At max positions ({len(positions)}/{self.MAX_POSITIONS})")
                return

            logger.info(f"📋 Processing {len(signals)} signals, {available_slots} slots available")

            # Process signals (highest score first, already sorted)
            bought = 0
            for signal in signals:
                if bought >= available_slots:
                    break

                symbol = signal['symbol']
                score = signal.get('score', 0)

                # Skip if already in position
                if symbol in positions:
                    logger.debug(f"⏩ {symbol} already in position")
                    continue

                # Skip if in cooldown
                if not self.check_cooldown(symbol):
                    continue

                # Validate price BEFORE attempting to buy
                is_valid, current_price, reason = self.validate_price(symbol, signal['price'])
                if not is_valid:
                    logger.info(f"⏩ {symbol} skipped: {reason}")
                    continue

                # Execute buy with validated price
                if self.execute_buy(signal, validated_price=current_price):
                    bought += 1
                    # Update positions for next iteration
                    positions = self.get_current_positions()

            if bought > 0:
                logger.info(f"🎯 Bought {bought} new positions")

        except Exception as e:
            logger.error(f"Error processing signals: {e}")

    def process_hot_signal(self) -> bool:
        """
        Check and process hot signals for fast-path execution.

        Hot signals (score >= 90) get priority processing every 5 seconds.

        Returns:
            True if a hot signal was processed
        """
        try:
            signal = self.signal_notifier.check_hot_signal()
            if not signal:
                return False

            symbol = signal['symbol']
            score = signal.get('score', 0)

            # Verify it's actually a hot signal
            if score < HOT_SIGNAL_MIN_SCORE:
                logger.debug(f"Signal score {score} below hot threshold {HOT_SIGNAL_MIN_SCORE}")
                self.signal_notifier.mark_processed()
                return False

            # Check if we can trade this signal
            positions = self.get_current_positions()
            if len(positions) >= self.MAX_POSITIONS:
                logger.debug("At max positions, skipping hot signal")
                self.signal_notifier.mark_processed()
                return False

            if symbol in positions:
                logger.debug(f"{symbol} already in position")
                self.signal_notifier.mark_processed()
                return False

            if not self.check_cooldown(symbol):
                self.signal_notifier.mark_processed()
                return False

            # Validate price for hot signal
            is_valid, current_price, reason = self.validate_price(symbol, signal['price'])
            if not is_valid:
                logger.info(f"🔥 Hot signal {symbol} skipped: {reason}")
                self.signal_notifier.mark_processed()
                return False

            # Execute the hot signal
            logger.info(f"🔥 HOT SIGNAL: {symbol} score={score}")
            if self.execute_buy(signal, validated_price=current_price):
                self.signal_notifier.mark_processed()
                return True
            else:
                self.signal_notifier.mark_processed()
                return False

        except Exception as e:
            logger.error(f"Error processing hot signal: {e}")
            return False

    def run_continuous(self, interval_seconds: int = 15):
        """
        Run buyer continuously with hot signal checking.

        - Hot signals checked every 5 seconds (fast path)
        - Regular signals processed every 15 seconds

        Args:
            interval_seconds: Main check interval for regular signals
        """
        hot_check_interval = HOT_CHECK_INTERVAL  # From config (5s)

        logger.info("=" * 80)
        logger.info("🚀 BUYER SERVICE v2.1 STARTING")
        logger.info(f"   Regular Interval: {interval_seconds}s")
        logger.info(f"   Hot Signal Check: {hot_check_interval}s")
        logger.info(f"   Max Positions: {self.MAX_POSITIONS}")
        logger.info(f"   Signal Max Age: {self.SIGNAL_MAX_AGE_SECONDS}s")
        logger.info(f"   Max Slippage: {self.MAX_SLIPPAGE_PCT*100}%")
        logger.info("=" * 80)

        last_regular_check = 0

        try:
            while True:
                try:
                    clock = self.api.get_clock()

                    if clock.is_open:
                        current_time = time.time()

                        # Always check for hot signals (fast path)
                        self.process_hot_signal()

                        # Check regular signals on main interval
                        if current_time - last_regular_check >= interval_seconds:
                            self.process_signals()
                            last_regular_check = current_time
                            logger.debug(f"Next regular check in {interval_seconds}s")

                        time.sleep(hot_check_interval)
                    else:
                        logger.debug("Market closed")
                        time.sleep(300)

                except Exception as e:
                    logger.error(f"Error: {e}")
                    time.sleep(60)

        except KeyboardInterrupt:
            logger.info("⚠️ Buyer stopped by user")


def main():
    """Entry point"""
    buyer = OrderBuyer()
    buyer.run_continuous(interval_seconds=15)


if __name__ == "__main__":
    main()
