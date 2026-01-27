"""
SELLER SERVICE (Bot 4)
Executes sell orders based on signals from monitor

Runs every 15 seconds with highest priority
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from core.shared_state import CooldownManager, get_state_dir, get_logs_dir, SafeJSONFile
from core.order_utils import OrderExecutor
from config import COOLDOWN_MINUTES

load_dotenv()

# Configure logging
logs_dir = get_logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'seller.log'), mode='a'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OrderSeller:
    """Executes sell orders from monitor signals"""
    
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

        # Cooldown tracking - use shared state manager
        state_dir = get_state_dir()
        self.cooldown_manager = CooldownManager(
            cooldowns_file=os.path.join(state_dir, 'cooldowns.json'),
            cooldown_minutes=COOLDOWN_MINUTES  # From config
        )
        
        self.sell_signals_file = os.path.join(state_dir, 'sell_signals.json')
        self.positions_file = os.path.join(state_dir, 'positions.json')
        self.trades_file = os.path.join(state_dir, 'trades.json')
        
        # Load state on startup
        self.load_state()
        
        logger.info("✅ Seller initialized")
    
    def load_sell_signals(self) -> List[Dict]:
        """Load sell signals from monitor"""
        try:
            with SafeJSONFile(self.sell_signals_file, 'r') as data:
                signals = data.get('signals', [])
                
                # Filter out stale signals (>2 min old)
                fresh_signals = []
                cutoff = datetime.now() - timedelta(minutes=2)
                
                for signal in signals:
                    signal_time = datetime.fromisoformat(signal['timestamp'])
                    if signal_time >= cutoff:
                        fresh_signals.append(signal)
                
                if fresh_signals:
                    logger.info(f"📥 Loaded {len(fresh_signals)} sell signals")
                
                return fresh_signals
            
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"❌ Error loading sell signals: {e}")
            return []
    
    def execute_sell(self, signal: Dict) -> bool:
        """
        Execute sell order using OrderExecutor for robust handling.

        Args:
            signal: Sell signal dict from monitor

        Returns:
            True if successful, False otherwise
        """
        symbol = signal['symbol']
        quantity = signal['quantity']
        reason = signal['reason']

        try:
            logger.info(f"SELLING {symbol} - Reason: {reason}")
            logger.info(f"   Exit Price: ${signal['price']:.2f}, Qty: {quantity}")

            # Use OrderExecutor for robust order handling
            success, result = self.order_executor.submit_and_wait(
                symbol=symbol,
                qty=quantity,
                side='sell'
            )

            if success:
                filled_price = result['filled_price']
                filled_qty = result.get('filled_qty', quantity)
                entry_price = signal.get('entry_price', filled_price)
                profit_pct = (filled_price - entry_price) / entry_price
                profit_dollar = (filled_price - entry_price) * filled_qty

                logger.info(f"SOLD {symbol} @ ${filled_price:.2f}")
                logger.info(f"   Entry: ${entry_price:.2f}, P&L: ${profit_dollar:.2f} ({profit_pct*100:+.1f}%)")

                # Log trade
                self.log_trade(symbol, signal, filled_price, profit_pct, profit_dollar)

                # Remove from positions
                self.remove_position(symbol)

                # Add cooldown
                self.add_cooldown(symbol)

                return True
            else:
                logger.warning(f"{symbol} sell order not filled: {result.get('reason', result.get('status'))}")
                return False

        except Exception as e:
            logger.error(f"Error selling {symbol}: {e}")
            return False
    
    def log_trade(
        self,
        symbol: str,
        signal: Dict,
        exit_price: float,
        profit_pct: float,
        profit_dollar: float
    ):
        """Log completed trade to history"""
        try:
            # Load existing trades (trades.json is a list, not a dict)
            trades = []
            try:
                with SafeJSONFile(self.trades_file, 'r') as data:
                    # trades.json is a list, so data.data is the list
                    if isinstance(data.data, list):
                        trades = list(data.data)  # Make a copy
            except (FileNotFoundError, AttributeError):
                trades = []
            
            # Create trade record
            entry_time_str = signal.get('entry_time', datetime.now().isoformat())
            
            trade = {
                'symbol': symbol,
                'entry_time': entry_time_str,
                'exit_time': datetime.now().isoformat(),
                'entry_price': signal.get('entry_price', exit_price),
                'exit_price': exit_price,
                'quantity': signal['quantity'],
                'pnl_pct': profit_pct,
                'pnl_dollar': profit_dollar,
                'hold_time_hours': self._calculate_hold_time(entry_time_str),
                'signal_score': signal.get('signal_score', 100),
                'acceleration': signal.get('acceleration', 0),
                'exit_reason': signal['reason']
            }
            
            trades.append(trade)
            
            # Save (trades.json is a list)
            with SafeJSONFile(self.trades_file, 'w') as file_data:
                file_data.data = trades
            
            logger.debug(f"💾 Logged trade for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error logging trade: {e}")
    
    def _calculate_hold_time(self, entry_time_str: str) -> float:
        """Calculate hold time in hours"""
        try:
            entry_time = datetime.fromisoformat(entry_time_str)
            exit_time = datetime.now()
            hold_time = (exit_time - entry_time).total_seconds() / 3600
            return hold_time
        except:
            return 0
    
    def remove_position(self, symbol: str):
        """Remove position from tracking"""
        try:
            with SafeJSONFile(self.positions_file, 'r') as data:
                positions = data.copy()
            
            if symbol in positions:
                with SafeJSONFile(self.positions_file, 'w') as file_data:
                    if symbol in file_data:
                        del file_data[symbol]
                
                logger.debug(f"🗑️  Removed {symbol} from positions")
        except FileNotFoundError:
            pass  # File doesn't exist, nothing to remove
        except Exception as e:
            logger.error(f"❌ Error removing position: {e}")
    
    def add_cooldown(self, symbol: str):
        """Add symbol to cooldown using shared state manager"""
        self.cooldown_manager.add_cooldown(symbol)
    
    def load_state(self):
        """Load state on startup"""
        try:
            logger.info("🔄 Loading state on startup...")
            
            # Cooldowns are already loaded by CooldownManager.__init__
            # Just log the current state
            cooldowns = self.cooldown_manager.cooldowns
            if cooldowns:
                logger.info(f"📥 Loaded {len(cooldowns)} active cooldowns")
            
            logger.info("✅ State loaded")
            
        except Exception as e:
            logger.error(f"❌ Error loading state: {e}")
    
    def process_sell_signals(self):
        """Process sell signals and execute sells"""
        try:
            # Load sell signals
            signals = self.load_sell_signals()
            
            if not signals:
                return
            
            # Execute sells
            sold = 0
            for signal in signals:
                if self.execute_sell(signal):
                    sold += 1
            
            if sold > 0:
                logger.info(f"✅ Sold {sold} positions")
            
            # Clear sell signals file after processing
            self.clear_sell_signals()
            
        except Exception as e:
            logger.error(f"❌ Error processing sell signals: {e}")
    
    def clear_sell_signals(self):
        """Clear processed sell signals"""
        try:
            with SafeJSONFile(self.sell_signals_file, 'w') as file_data:
                file_data['timestamp'] = datetime.now().isoformat()
                file_data['signals'] = []
        except Exception as e:
            logger.error(f"❌ Error clearing sell signals: {e}")
    
    def run_continuous(self, interval_seconds: int = 15):
        """
        Run seller continuously
        
        Args:
            interval_seconds: Check interval (default 15s - high priority)
        """
        logger.info("="*80)
        logger.info("🚀 SELLER SERVICE STARTING")
        logger.info(f"   Check Interval: {interval_seconds}s (HIGH PRIORITY)")
        logger.info("="*80)
        
        try:
            while True:
                # Check if market is open
                try:
                    clock = self.api.get_clock()
                    
                    if clock.is_open:
                        self.process_sell_signals()
                        time.sleep(interval_seconds)
                    else:
                        logger.debug("🌙 Market closed")
                        time.sleep(300)
                        
                except Exception as e:
                    logger.error(f"❌ Error: {e}")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            logger.info("⚠️  Seller stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")


def main():
    """Entry point"""
    seller = OrderSeller()
    seller.run_continuous(interval_seconds=15)


if __name__ == "__main__":
    main()
