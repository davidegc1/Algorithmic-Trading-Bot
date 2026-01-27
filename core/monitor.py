"""
MONITOR SERVICE (Bot 3)
Tracks open positions and generates sell signals

Runs every 60 seconds with high priority
API Budget: ~40 calls per minute (20 positions * 2 calls each = safe)
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from core.shared_state import PositionManager, get_state_dir, get_logs_dir, SafeJSONFile
from config import (
    STOP_LOSS_PCT,
    BREAKEVEN_PROFIT,
    TRAILING_STOPS,
    DECEL_EXIT_THRESHOLD,
    MIN_PROFIT_FOR_DECEL_CHECK,
)

load_dotenv()

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'monitor.log'), mode='a'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PositionMonitor:
    """Monitors positions and generates sell signals"""
    
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
        
        # Risk management - from config (single source of truth)
        self.STOP_LOSS_PCT = STOP_LOSS_PCT          # 2.5% from config
        self.BREAKEVEN_PROFIT = BREAKEVEN_PROFIT    # 5% from config

        # Trailing stops - from config
        self.TRAILING_STOPS = TRAILING_STOPS        # Dict from config

        # Deceleration - from config
        self.DECEL_EXIT_THRESHOLD = DECEL_EXIT_THRESHOLD          # 0.5
        self.MIN_PROFIT_FOR_DECEL_CHECK = MIN_PROFIT_FOR_DECEL_CHECK  # 5%
        
        # Position tracking - use shared state manager
        state_dir = get_state_dir()
        self.position_manager = PositionManager(
            positions_file=os.path.join(state_dir, 'positions.json')
        )
        
        self.sell_signals_file = os.path.join(state_dir, 'sell_signals.json')
        
        # Track highest prices
        self.highest_prices = {}
        
        # Load and reconcile state on startup
        self.load_state()
        
        logger.info("✅ Monitor initialized")
    
    def load_position_info(self) -> Dict:
        """Load position info using shared position manager"""
        return self.position_manager.get_positions()
    
    def save_position_info(self, positions: Dict):
        """Save updated position info using shared position manager"""
        # Update all positions
        for symbol, info in positions.items():
            self.position_manager.add_position(symbol, info)
    
    def load_state(self):
        """Load and reconcile state on startup"""
        try:
            logger.info("🔄 Loading state on startup...")
            
            # Get current positions from Alpaca
            alpaca_positions = self.get_current_positions()
            
            # Convert Alpaca format to format expected by reconcile
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
            logger.error(f"❌ Error loading state: {e}")
    
    def get_current_positions(self) -> Dict:
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
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return {}
    
    def get_historical_bars(self, symbol: str, timeframe: str, limit: int = 10) -> pd.DataFrame:
        """Get historical bars"""
        try:
            bars = self.api.get_bars(symbol, timeframe, limit=limit).df
            
            if bars.empty:
                return pd.DataFrame()
            
            if not isinstance(bars.index, pd.DatetimeIndex):
                bars.index = pd.to_datetime(bars.index)
            
            return bars
            
        except Exception as e:
            logger.debug(f"⚠️  Error getting bars for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_acceleration(
        self,
        symbol: str,
        current_price: float
    ) -> float:
        """Calculate current acceleration"""
        try:
            bars_2min = self.get_historical_bars(symbol, '2Min', limit=10)
            bars_5min = self.get_historical_bars(symbol, '5Min', limit=10)
            
            if bars_2min.empty or bars_5min.empty:
                return 0
            
            if len(bars_2min) < 2 or len(bars_5min) < 2:
                return 0
            
            price_2min_ago = bars_2min.iloc[-2]['close']
            price_5min_ago = bars_5min.iloc[-2]['close']
            
            if price_2min_ago <= 0 or price_5min_ago <= 0:
                return 0
            
            V1 = (current_price / price_2min_ago - 1) / 2
            V2 = (current_price / price_5min_ago - 1) / 5
            
            MIN_VELOCITY = 0.0001
            if abs(V2) < MIN_VELOCITY:
                return 0
            
            acceleration = V1 / V2 if V2 != 0 else 0
            
            return acceleration

        except Exception as e:
            logger.debug(f"Error calculating acceleration for {symbol}: {e}")
            return 0

    def calculate_atr(self, symbol: str, period: int = 14) -> float:
        """
        Calculate Average True Range for dynamic stop sizing.

        ATR measures volatility - higher ATR means wider stops needed.

        Args:
            symbol: Stock symbol
            period: ATR period (default 14)

        Returns:
            ATR value or 0 if calculation fails
        """
        try:
            bars = self.get_historical_bars(symbol, '5Min', limit=period + 5)
            if bars.empty or len(bars) < period + 1:
                return 0

            highs = bars['high'].values
            lows = bars['low'].values
            closes = bars['close'].values

            # Calculate True Range for each bar
            true_ranges = []
            for i in range(1, len(bars)):
                high_low = highs[i] - lows[i]
                high_close = abs(highs[i] - closes[i-1])
                low_close = abs(lows[i] - closes[i-1])
                true_ranges.append(max(high_low, high_close, low_close))

            # Calculate ATR as average of True Ranges
            if len(true_ranges) >= period:
                atr = sum(true_ranges[-period:]) / period
                return atr

            return 0

        except Exception as e:
            logger.debug(f"Error calculating ATR for {symbol}: {e}")
            return 0

    def calculate_dynamic_stop(self, symbol: str, entry_price: float, atr_multiplier: float = 2.0) -> float:
        """
        Calculate dynamic stop loss based on ATR.

        Args:
            symbol: Stock symbol
            entry_price: Entry price
            atr_multiplier: Multiple of ATR for stop distance (default 2.0)

        Returns:
            Stop loss price
        """
        atr = self.calculate_atr(symbol)

        if atr > 0:
            stop_distance = atr * atr_multiplier
            dynamic_stop = entry_price - stop_distance
            # Don't let stop be more than 5% away
            min_stop = entry_price * (1 - 0.05)
            return max(dynamic_stop, min_stop)

        # Fallback to fixed percentage
        return entry_price * (1 - self.STOP_LOSS_PCT)

    def check_exit_conditions(
        self,
        symbol: str,
        position_info: Dict,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Check if position should be exited
        
        Returns:
            (should_exit, reason)
        """
        try:
            entry_price = position_info.get('entry_price', current_price)
            stop_loss = position_info.get('stop_loss', entry_price * 0.975)
            
            # Calculate profit
            profit_pct = (current_price - entry_price) / entry_price
            
            # Track highest price
            if symbol not in self.highest_prices:
                self.highest_prices[symbol] = current_price
            else:
                if current_price > self.highest_prices[symbol]:
                    self.highest_prices[symbol] = current_price
            
            highest_price = self.highest_prices[symbol]
            
            # 1. HARD STOP LOSS
            if current_price <= stop_loss:
                logger.info(f"🛑 {symbol} hit stop loss: ${current_price:.2f} <= ${stop_loss:.2f}")
                return True, f"STOP_LOSS"
            
            # 2. BREAK-EVEN PROTECTION
            if profit_pct >= self.BREAKEVEN_PROFIT:
                if stop_loss < entry_price:
                    position_info['stop_loss'] = entry_price
                    logger.info(f"🔒 {symbol} stop moved to break-even @ ${entry_price:.2f}")
            
            # 3. TRAILING STOP
            if profit_pct >= 0.10:
                # Determine trailing percentage
                trailing_pct = 0.05  # Default
                for profit_threshold, trail_pct in sorted(self.TRAILING_STOPS.items(), reverse=True):
                    if profit_pct >= profit_threshold:
                        trailing_pct = trail_pct
                        break
                
                # Calculate trailing stop
                trailing_stop_price = highest_price * (1 - trailing_pct)
                
                # Update stop if higher
                if trailing_stop_price > stop_loss:
                    position_info['stop_loss'] = trailing_stop_price
                    stop_loss = trailing_stop_price
                
                # Check if trailing stop hit
                if current_price <= stop_loss:
                    logger.info(f"📉 {symbol} hit trailing stop: ${current_price:.2f} <= ${stop_loss:.2f}")
                    return True, f"TRAILING_STOP_{int(trailing_pct*100)}PCT"
            
            # 4. DECELERATION EXIT
            if profit_pct > self.MIN_PROFIT_FOR_DECEL_CHECK:
                acceleration = self.calculate_acceleration(symbol, current_price)

                if 0 < acceleration < self.DECEL_EXIT_THRESHOLD:
                    logger.info(f"{symbol} decelerating: A={acceleration:.2f}, profit={profit_pct*100:.1f}%")
                    return True, "DECELERATION"

            # 5. TIME-BASED EXIT (no significant movement)
            entry_time_str = position_info.get('entry_time')
            if entry_time_str:
                try:
                    entry_time = datetime.fromisoformat(entry_time_str)
                    hold_time_minutes = (datetime.now() - entry_time).total_seconds() / 60

                    # Exit if held > 30 minutes with less than 1% move (stagnant position)
                    if hold_time_minutes > 30 and abs(profit_pct) < 0.01:
                        logger.info(f"{symbol} time exit: no movement in {hold_time_minutes:.0f} min")
                        return True, "TIME_EXIT_STAGNANT"

                    # Exit if held > 60 minutes with less than 2% profit (not working)
                    if hold_time_minutes > 60 and profit_pct < 0.02:
                        logger.info(f"{symbol} time exit: only {profit_pct*100:.1f}% after {hold_time_minutes:.0f} min")
                        return True, "TIME_EXIT_UNDERPERFORM"

                except (ValueError, TypeError):
                    pass  # Invalid entry time, skip check

            return False, ""

        except Exception as e:
            logger.error(f"Error checking exit for {symbol}: {e}")
            return False, ""
    
    def generate_sell_signals(self):
        """Generate sell signals for positions that should be exited"""
        try:
            # Get current positions from Alpaca
            alpaca_positions = self.get_current_positions()
            
            if not alpaca_positions:
                logger.info("No positions to monitor")
                return
            
            logger.info(f"📊 Monitoring {len(alpaca_positions)} positions")
            
            # Load position info
            position_info = self.load_position_info()
            
            # Check each position
            sell_signals = []
            
            for symbol, alpaca_pos in alpaca_positions.items():
                current_price = alpaca_pos['current_price']
                profit_pct = alpaca_pos['unrealized_plpc']
                
                # Get stored position info
                if symbol not in position_info:
                    # Create default info from Alpaca data
                    position_info[symbol] = {
                        'entry_price': alpaca_pos['entry_price'],
                        'quantity': alpaca_pos['qty'],
                        'entry_time': datetime.now().isoformat(),
                        'stop_loss': alpaca_pos['entry_price'] * (1 - self.STOP_LOSS_PCT)
                    }
                
                info = position_info[symbol]
                
                # Check exit conditions
                should_exit, reason = self.check_exit_conditions(symbol, info, current_price)
                
                if should_exit:
                    # Generate sell signal
                    sell_signal = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'price': current_price,
                        'quantity': alpaca_pos['qty'],
                        'reason': reason,
                        'entry_price': info.get('entry_price', alpaca_pos['entry_price']),
                        'profit_pct': profit_pct * 100
                    }
                    
                    sell_signals.append(sell_signal)
                    logger.info(f"🔴 SELL SIGNAL: {symbol} @ ${current_price:.2f} - {reason} ({profit_pct*100:+.1f}%)")
                else:
                    # Log position status
                    logger.info(f"   {symbol}: ${current_price:.2f} ({profit_pct*100:+.1f}%), "
                               f"Stop: ${info['stop_loss']:.2f}")
            
            # Save updated position info
            self.save_position_info(position_info)
            
            # Save sell signals
            if sell_signals:
                self.save_sell_signals(sell_signals)
                logger.info(f"✅ Generated {len(sell_signals)} sell signals")
            
        except Exception as e:
            logger.error(f"❌ Error generating sell signals: {e}")
    
    def save_sell_signals(self, signals: List[Dict]):
        """Save sell signals to file"""
        try:
            with SafeJSONFile(self.sell_signals_file, 'w') as file_data:
                file_data['timestamp'] = datetime.now().isoformat()
                file_data['signals'] = signals
            
            logger.debug(f"Saved {len(signals)} sell signals")

        except Exception as e:
            logger.error(f"Error saving sell signals: {e}")

    def run_continuous(self, interval_seconds: int = 30, use_streaming: bool = True):
        """
        Run monitor continuously with optional WebSocket streaming.

        Args:
            interval_seconds: Polling interval for fallback mode (default 30s)
            use_streaming: Try to use WebSocket streaming (default True)
        """
        logger.info("="*80)
        logger.info("MONITOR SERVICE STARTING")
        logger.info(f"   Polling Interval: {interval_seconds}s")
        logger.info(f"   Stop Loss: {self.STOP_LOSS_PCT*100}%")
        logger.info(f"   Streaming: {'Enabled' if use_streaming else 'Disabled'}")
        logger.info("="*80)

        # Try to use streaming if enabled
        if use_streaming:
            try:
                from core.price_stream import RealTimeMonitor
                self._run_with_streaming()
                return  # If streaming works, we don't fall through
            except ImportError:
                logger.warning("Streaming not available, falling back to polling")
            except Exception as e:
                logger.warning(f"Streaming failed: {e}, falling back to polling")

        # Fallback to polling
        self._run_polling(interval_seconds)

    def _run_with_streaming(self):
        """Run with WebSocket streaming for real-time monitoring."""
        import asyncio
        from core.price_stream import PriceStreamManager

        def on_price_update(symbol: str, bid: float, ask: float, mid: float):
            """Handle real-time price update."""
            position_info = self.load_position_info()
            if symbol not in position_info:
                return

            info = position_info[symbol]
            current_price = mid

            # Check exit conditions
            should_exit, reason = self.check_exit_conditions(symbol, info, current_price)

            if should_exit:
                # Get position details from Alpaca
                try:
                    positions = self.get_current_positions()
                    if symbol in positions:
                        alpaca_pos = positions[symbol]
                        sell_signal = {
                            'symbol': symbol,
                            'timestamp': datetime.now().isoformat(),
                            'price': current_price,
                            'quantity': alpaca_pos['qty'],
                            'reason': reason,
                            'entry_price': info.get('entry_price', alpaca_pos['entry_price']),
                            'profit_pct': (current_price - info.get('entry_price', current_price)) / info.get('entry_price', current_price) * 100
                        }
                        self.save_sell_signals([sell_signal])
                        logger.info(f"REAL-TIME EXIT: {symbol} @ ${current_price:.2f} - {reason}")
                except Exception as e:
                    logger.error(f"Error generating sell signal: {e}")

        stream_manager = PriceStreamManager(on_price_update=on_price_update)

        async def run_stream():
            # Get current positions
            positions = self.get_current_positions()
            if positions:
                await stream_manager.subscribe(list(positions.keys()))

            # Run stream with periodic position refresh
            refresh_interval = 60  # Refresh positions every 60s
            last_refresh = time.time()

            while True:
                try:
                    clock = self.api.get_clock()
                    if not clock.is_open:
                        logger.info("Market closed, waiting...")
                        await asyncio.sleep(300)
                        continue

                    # Refresh positions periodically
                    if time.time() - last_refresh > refresh_interval:
                        positions = self.get_current_positions()
                        current_symbols = set(positions.keys())
                        subscribed = stream_manager.subscribed_symbols

                        # Subscribe to new positions
                        new_symbols = current_symbols - subscribed
                        if new_symbols:
                            await stream_manager.subscribe(list(new_symbols))

                        # Unsubscribe from closed positions
                        closed_symbols = subscribed - current_symbols
                        if closed_symbols:
                            await stream_manager.unsubscribe(list(closed_symbols))

                        # Also run traditional check as backup
                        self.generate_sell_signals()
                        last_refresh = time.time()

                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    await asyncio.sleep(10)

        try:
            asyncio.run(run_stream())
        except KeyboardInterrupt:
            stream_manager.stop()
            logger.info("Monitor stopped by user")

    def _run_polling(self, interval_seconds: int):
        """Run with traditional polling."""
        try:
            while True:
                try:
                    clock = self.api.get_clock()

                    if clock.is_open:
                        self.generate_sell_signals()
                        logger.info(f"Next check in {interval_seconds}s...")
                        time.sleep(interval_seconds)
                    else:
                        logger.info("Market closed")
                        time.sleep(300)

                except Exception as e:
                    logger.error(f"Error: {e}")
                    time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")


def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description='Position Monitor')
    parser.add_argument('--no-stream', action='store_true', help='Disable WebSocket streaming')
    parser.add_argument('--interval', type=int, default=30, help='Polling interval in seconds')
    args = parser.parse_args()

    monitor = PositionMonitor()
    monitor.run_continuous(
        interval_seconds=args.interval,
        use_streaming=not args.no_stream
    )


if __name__ == "__main__":
    main()
