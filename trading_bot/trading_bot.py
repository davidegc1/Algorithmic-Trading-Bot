"""
VELOCITY + ACCELERATION MOMENTUM TRADING BOT
Complete automated trading system with Alpaca API integration

Strategy: Hunt volatility, cut losses instantly, never cap winners
Edge: Velocity + Acceleration detection on multi-timeframe analysis
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from dataclasses import dataclass
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Track position details"""
    symbol: str
    entry_price: float
    quantity: int
    entry_time: datetime
    stop_loss: float
    trailing_stop_pct: float
    highest_price: float
    signal_score: int


@dataclass
class Signal:
    """Trading signal with all metrics"""
    symbol: str
    current_price: float
    breakout_5min: float
    breakout_2min: float
    volume_ratio: float
    is_15min_green: bool
    v1: float  # Velocity last 2 min
    v2: float  # Velocity last 5 min
    v3: float  # Velocity last 15 min
    acceleration: float
    score: int
    position_size_pct: float  # 5% or 7%


class VelocityAccelerationBot:
    """Main trading bot with V+A strategy"""
    
    def __init__(self, paper_trading: bool = True):
        """Initialize the bot"""
        
        # Alpaca API setup
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        
        if paper_trading:
            self.base_url = 'https://paper-api.alpaca.markets'
            logger.info("🔧 Running in PAPER TRADING mode")
        else:
            self.base_url = 'https://api.alpaca.markets'
            logger.warning("⚠️  Running in LIVE TRADING mode")
        
        self.api = tradeapi.REST(
            self.api_key,
            self.api_secret,
            self.base_url,
            api_version='v2'
        )
        
        # Strategy parameters
        self.MAX_POSITIONS = 20
        self.POSITION_SIZE_STANDARD = 0.05  # 5%
        self.POSITION_SIZE_STRONG = 0.07    # 7%
        self.STOP_LOSS_PCT = 0.025          # 2.5%
        self.BREAKEVEN_PROFIT = 0.10        # 10%
        
        # Trailing stop tiers
        self.TRAILING_STOPS = {
            0.10: 0.05,   # +10-20%: 5% trailing
            0.20: 0.10,   # +20-40%: 10% trailing
            0.40: 0.15,   # +40-70%: 15% trailing
            0.70: 0.20    # +70%+: 20% trailing
        }
        
        # Entry thresholds
        self.BREAKOUT_5MIN_PCT = 0.04      # 4%
        self.BREAKOUT_2MIN_PCT = 0.03      # 3%
        self.VOLUME_RATIO_MIN = 2.0        # 2x average
        self.ACCELERATION_MIN = 1.2        # A > 1.2
        self.MIN_ENTRY_SCORE = 70          # Minimum to enter
        
        # Volatility requirements
        self.MIN_ATR_PCT = 0.05            # 5% daily ATR
        
        # Cooldown tracking
        self.cooldown_until = {}           # symbol -> datetime
        self.COOLDOWN_MINUTES = 15
        
        # Active positions
        self.positions: Dict[str, Position] = {}
        
        # Universe of stocks
        self.universe: List[str] = []
        
        # Trade logger
        from utils import TradeLogger
        self.trade_logger = TradeLogger('trades.json')
        
        logger.info("✅ Bot initialized successfully")
    
    
    def load_universe(self, filepath: str = None) -> List[str]:
        """
        Load trading universe from file or generate dynamically
        
        Args:
            filepath: Path to CSV with stock symbols
            
        Returns:
            List of stock symbols
        """
        if filepath and os.path.exists(filepath):
            df = pd.read_csv(filepath)
            self.universe = df['symbol'].tolist() if 'symbol' in df.columns else df.iloc[:, 0].tolist()
            logger.info(f"📋 Loaded {len(self.universe)} stocks from {filepath}")
        else:
            # Default high-volatility watchlist
            self.universe = [
                # Crypto-related
                'MARA', 'RIOT', 'COIN', 'CLSK', 'CIFR',
                # Biotech
                'SAVA', 'TBPH', 'IRWD', 'MNMD', 'ATAI',
                # Small-cap tech
                'IONQ', 'SOFI', 'HOOD', 'UPST', 'AFRM',
                # EV/Battery
                'LCID', 'RIVN', 'PLUG', 'BLNK', 'CHPT',
                # Cannabis
                'TLRY', 'CGC', 'SNDL', 'ACB', 'HEXO',
                # High-beta
                'GME', 'AMC', 'BBBY', 'FUBO', 'WISH',
                # Volatile small caps
                'SPCE', 'OPEN', 'BIRD', 'SKLZ', 'DKNG'
            ]
            logger.info(f"📋 Using default watchlist: {len(self.universe)} stocks")
        
        return self.universe
    
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            account = self.api.get_account()
            equity = float(account.equity)
            cash = float(account.cash)
            buying_power = float(account.buying_power)
            
            info = {
                'equity': equity,
                'cash': cash,
                'buying_power': buying_power,
                'portfolio_value': equity
            }
            
            logger.info(f"💰 Account - Equity: ${equity:,.2f}, Cash: ${cash:,.2f}")
            return info
            
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return {}
    
    
    def get_historical_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get historical price data
        
        Args:
            symbol: Stock symbol
            timeframe: '1Min', '2Min', '5Min', '15Min', etc.
            limit: Number of bars to retrieve
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            bars = self.api.get_bars(
                symbol,
                timeframe,
                limit=limit
            ).df
            
            if bars.empty:
                logger.warning(f"⚠️  No data for {symbol}")
                return pd.DataFrame()
            
            # Convert index to datetime if needed
            if not isinstance(bars.index, pd.DatetimeIndex):
                bars.index = pd.to_datetime(bars.index)
            
            return bars
            
        except Exception as e:
            logger.error(f"❌ Error getting bars for {symbol}: {e}")
            return pd.DataFrame()
    
    
    def calculate_velocity_acceleration(
        self, 
        bars_2min: pd.DataFrame,
        bars_5min: pd.DataFrame,
        bars_15min: pd.DataFrame,
        current_price: float
    ) -> Tuple[float, float, float, float]:
        """
        Calculate V1, V2, V3, and Acceleration
        
        Returns:
            (V1, V2, V3, Acceleration)
        """
        try:
            # Get prices at different lookback periods
            price_2min_ago = bars_2min.iloc[-2]['close'] if len(bars_2min) >= 2 else current_price
            price_5min_ago = bars_5min.iloc[-2]['close'] if len(bars_5min) >= 2 else current_price
            price_15min_ago = bars_15min.iloc[-4]['close'] if len(bars_15min) >= 4 else current_price
            
            # Calculate velocity (% change per minute)
            V1 = (current_price / price_2min_ago - 1) / 2 if price_2min_ago > 0 else 0
            V2 = (current_price / price_5min_ago - 1) / 5 if price_5min_ago > 0 else 0
            V3 = (current_price / price_15min_ago - 1) / 15 if price_15min_ago > 0 else 0
            
            # Calculate acceleration
            acceleration = V1 / V2 if V2 != 0 else 0
            
            return V1, V2, V3, acceleration
            
        except Exception as e:
            logger.error(f"❌ Error calculating V+A: {e}")
            return 0, 0, 0, 0
    
    
    def check_entry_signal(self, symbol: str) -> Optional[Signal]:
        """
        Check if stock meets entry criteria
        
        Returns:
            Signal object if valid, None otherwise
        """
        try:
            # Check cooldown
            if symbol in self.cooldown_until:
                if datetime.now() < self.cooldown_until[symbol]:
                    return None
                else:
                    del self.cooldown_until[symbol]
            
            # Get multi-timeframe data
            bars_2min = self.get_historical_bars(symbol, '2Min', limit=10)
            bars_5min = self.get_historical_bars(symbol, '5Min', limit=20)
            bars_15min = self.get_historical_bars(symbol, '15Min', limit=30)
            
            if bars_5min.empty:
                return None
            
            current_price = bars_5min.iloc[-1]['close']
            
            # Calculate velocity and acceleration
            V1, V2, V3, acceleration = self.calculate_velocity_acceleration(
                bars_2min, bars_5min, bars_15min, current_price
            )
            
            # CORE REQUIREMENTS (must have all 3)
            score = 0
            
            # 1. 5-min breakout >4%
            low_5min = bars_5min.tail(1)['low'].iloc[0]
            breakout_5min_pct = (current_price - low_5min) / low_5min
            if breakout_5min_pct >= self.BREAKOUT_5MIN_PCT:
                score += 25
            else:
                return None  # REQUIRED
            
            # 2. Volume confirmation >2x
            current_volume = bars_5min.iloc[-1]['volume']
            avg_volume = bars_5min['volume'].tail(20).mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            if volume_ratio >= self.VOLUME_RATIO_MIN:
                score += 20
            else:
                return None  # REQUIRED
            
            # 3. 15-min chart is green
            is_15min_green = bars_15min.iloc[-1]['close'] > bars_15min.iloc[-1]['open']
            if is_15min_green:
                score += 10
            else:
                return None  # REQUIRED
            
            # BONUS POINTS
            
            # 4. 2-min breakout >3%
            if not bars_2min.empty:
                low_2min = bars_2min.tail(1)['low'].iloc[0]
                breakout_2min_pct = (current_price - low_2min) / low_2min
                if breakout_2min_pct >= self.BREAKOUT_2MIN_PCT:
                    score += 15
            
            # 5. Velocity ratio (V1 > V2)
            if V1 > V2:
                score += 15
            
            # 6. Acceleration >1.2
            if acceleration >= self.ACCELERATION_MIN:
                score += 15
            elif acceleration >= 1.0:
                score += 10
            
            # Determine position size
            position_size_pct = self.POSITION_SIZE_STRONG if score >= 90 else self.POSITION_SIZE_STANDARD
            
            # Create signal
            signal = Signal(
                symbol=symbol,
                current_price=current_price,
                breakout_5min=breakout_5min_pct * 100,
                breakout_2min=breakout_2min_pct * 100 if not bars_2min.empty else 0,
                volume_ratio=volume_ratio,
                is_15min_green=is_15min_green,
                v1=V1,
                v2=V2,
                v3=V3,
                acceleration=acceleration,
                score=score,
                position_size_pct=position_size_pct
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error checking entry for {symbol}: {e}")
            return None
    
    
    def execute_entry(self, signal: Signal) -> bool:
        """
        Execute entry trade
        
        Args:
            signal: Signal object with entry details
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already at max positions
            if len(self.positions) >= self.MAX_POSITIONS:
                logger.info(f"⚠️  Max positions reached ({self.MAX_POSITIONS}), skipping {signal.symbol}")
                return False
            
            # Check if already in position
            if signal.symbol in self.positions:
                logger.info(f"⚠️  Already in position for {signal.symbol}")
                return False
            
            # Get account info
            account_info = self.get_account_info()
            if not account_info:
                return False
            
            # Calculate position size
            portfolio_value = account_info['equity']
            position_value = portfolio_value * signal.position_size_pct
            quantity = int(position_value / signal.current_price)
            
            if quantity <= 0:
                logger.warning(f"⚠️  Calculated quantity is 0 for {signal.symbol}")
                return False
            
            # Place market order
            logger.info(f"🚀 ENTERING {signal.symbol} - Score: {signal.score}, Size: {signal.position_size_pct*100:.0f}%")
            logger.info(f"   Price: ${signal.current_price:.2f}, Qty: {quantity}, A: {signal.acceleration:.2f}")
            
            order = self.api.submit_order(
                symbol=signal.symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            # Wait for fill
            time.sleep(2)
            order = self.api.get_order(order.id)
            
            if order.status == 'filled':
                filled_price = float(order.filled_avg_price)
                
                # Calculate stop loss
                stop_loss = filled_price * (1 - self.STOP_LOSS_PCT)
                
                # Create position tracking
                position = Position(
                    symbol=signal.symbol,
                    entry_price=filled_price,
                    quantity=quantity,
                    entry_time=datetime.now(),
                    stop_loss=stop_loss,
                    trailing_stop_pct=0.05,  # Start with 5%
                    highest_price=filled_price,
                    signal_score=signal.score
                )
                
                self.positions[signal.symbol] = position
                
                logger.info(f"✅ FILLED {signal.symbol} @ ${filled_price:.2f}, Stop: ${stop_loss:.2f}")
                return True
            else:
                logger.warning(f"⚠️  Order not filled: {order.status}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing entry for {signal.symbol}: {e}")
            return False
    
    
    def check_exit_conditions(self, symbol: str, position: Position) -> Tuple[bool, str]:
        """
        Check if position should be exited
        
        Returns:
            (should_exit, reason)
        """
        try:
            # Get current price
            bars_5min = self.get_historical_bars(symbol, '5Min', limit=5)
            if bars_5min.empty:
                return False, ""
            
            current_price = bars_5min.iloc[-1]['close']
            
            # Calculate profit
            profit_pct = (current_price - position.entry_price) / position.entry_price
            
            # Update highest price
            if current_price > position.highest_price:
                position.highest_price = current_price
            
            # 1. HARD STOP LOSS (-2.5%)
            if current_price <= position.stop_loss:
                return True, f"STOP LOSS (-{self.STOP_LOSS_PCT*100:.1f}%)"
            
            # 2. BREAK-EVEN PROTECTION (move stop to entry at +10%)
            if profit_pct >= self.BREAKEVEN_PROFIT and position.stop_loss < position.entry_price:
                position.stop_loss = position.entry_price
                logger.info(f"🔒 {symbol} - Stop moved to break-even @ ${position.entry_price:.2f}")
            
            # 3. TRAILING STOP (graduated based on profit level)
            if profit_pct >= 0.10:
                # Determine trailing stop percentage
                for profit_threshold, trail_pct in sorted(self.TRAILING_STOPS.items(), reverse=True):
                    if profit_pct >= profit_threshold:
                        position.trailing_stop_pct = trail_pct
                        break
                
                # Calculate trailing stop price
                trailing_stop_price = position.highest_price * (1 - position.trailing_stop_pct)
                
                # Update stop if trailing is higher
                if trailing_stop_price > position.stop_loss:
                    position.stop_loss = trailing_stop_price
                
                # Check if trailing stop hit
                if current_price <= position.stop_loss:
                    return True, f"TRAILING STOP ({position.trailing_stop_pct*100:.0f}% trail, +{profit_pct*100:.1f}% profit)"
            
            # 4. DECELERATION EXIT (if in profit)
            if profit_pct > 0.05:  # Only check if >5% profit
                bars_2min = self.get_historical_bars(symbol, '2Min', limit=10)
                bars_15min = self.get_historical_bars(symbol, '15Min', limit=30)
                
                V1, V2, V3, acceleration = self.calculate_velocity_acceleration(
                    bars_2min, bars_5min, bars_15min, current_price
                )
                
                # Sharp deceleration = exit immediately
                if acceleration < 0.5 and acceleration > 0:
                    return True, f"DECELERATION (A={acceleration:.2f}, +{profit_pct*100:.1f}% profit)"
                
                # Moderate deceleration = tighten stop
                elif acceleration < 0.8 and acceleration > 0:
                    tighter_stop = position.highest_price * (1 - position.trailing_stop_pct + 0.05)
                    if tighter_stop > position.stop_loss:
                        position.stop_loss = tighter_stop
                        logger.info(f"⚠️  {symbol} - Decelerating (A={acceleration:.2f}), stop tightened to ${position.stop_loss:.2f}")
            
            return False, ""
            
        except Exception as e:
            logger.error(f"❌ Error checking exit for {symbol}: {e}")
            return False, ""
    
    
    def execute_exit(self, symbol: str, reason: str) -> bool:
        """
        Execute exit trade
        
        Args:
            symbol: Stock symbol
            reason: Reason for exit
            
        Returns:
            True if successful, False otherwise
        """
        try:
            position = self.positions[symbol]
            
            logger.info(f"🔴 EXITING {symbol} - Reason: {reason}")
            
            # Place market sell order
            order = self.api.submit_order(
                symbol=symbol,
                qty=position.quantity,
                side='sell',
                type='market',
                time_in_force='day'
            )
            
            # Wait for fill
            time.sleep(2)
            order = self.api.get_order(order.id)
            
            if order.status == 'filled':
                exit_price = float(order.filled_avg_price)
                profit_pct = (exit_price - position.entry_price) / position.entry_price
                profit_dollar = (exit_price - position.entry_price) * position.quantity
                
                logger.info(f"✅ SOLD {symbol} @ ${exit_price:.2f}")
                logger.info(f"   Entry: ${position.entry_price:.2f}, P&L: ${profit_dollar:.2f} ({profit_pct*100:+.1f}%)")
                
                # Log trade to history file
                self.trade_logger.log_trade(
                    symbol=symbol,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    quantity=position.quantity,
                    entry_time=position.entry_time,
                    exit_time=datetime.now(),
                    signal_score=position.signal_score,
                    acceleration=0,  # Could track exit acceleration
                    exit_reason=reason
                )
                
                # Remove from positions
                del self.positions[symbol]
                
                # Add to cooldown
                self.cooldown_until[symbol] = datetime.now() + timedelta(minutes=self.COOLDOWN_MINUTES)
                
                return True
            else:
                logger.warning(f"⚠️  Exit order not filled: {order.status}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing exit for {symbol}: {e}")
            return False
    
    
    def scan_and_trade(self):
        """Main trading loop - scan universe and execute trades"""
        
        logger.info("="*80)
        logger.info("🔍 SCANNING UNIVERSE FOR SIGNALS")
        logger.info("="*80)
        
        signals = []
        
        # Scan all stocks in universe
        for symbol in self.universe:
            signal = self.check_entry_signal(symbol)
            if signal and signal.score >= self.MIN_ENTRY_SCORE:
                signals.append(signal)
                logger.info(f"📊 {symbol}: Score={signal.score}, A={signal.acceleration:.2f}, "
                           f"5min={signal.breakout_5min:.1f}%, Vol={signal.volume_ratio:.1f}x")
        
        # Sort by score (best first)
        signals.sort(key=lambda x: x.score, reverse=True)
        
        # Execute entries (up to position limit)
        available_slots = self.MAX_POSITIONS - len(self.positions)
        for signal in signals[:available_slots]:
            if signal.score >= self.MIN_ENTRY_SCORE:
                self.execute_entry(signal)
        
        if not signals:
            logger.info("   No qualifying signals found")
        
        logger.info(f"📈 Active Positions: {len(self.positions)}/{self.MAX_POSITIONS}")
    
    
    def manage_positions(self):
        """Check and manage all open positions"""
        
        if not self.positions:
            return
        
        logger.info("="*80)
        logger.info("📊 MANAGING POSITIONS")
        logger.info("="*80)
        
        symbols_to_exit = []
        
        for symbol, position in self.positions.items():
            should_exit, reason = self.check_exit_conditions(symbol, position)
            
            if should_exit:
                symbols_to_exit.append((symbol, reason))
            else:
                # Log position status
                bars = self.get_historical_bars(symbol, '5Min', limit=2)
                if not bars.empty:
                    current_price = bars.iloc[-1]['close']
                    profit_pct = (current_price - position.entry_price) / position.entry_price
                    logger.info(f"   {symbol}: ${current_price:.2f} ({profit_pct*100:+.1f}%), "
                               f"Stop: ${position.stop_loss:.2f}")
        
        # Execute exits
        for symbol, reason in symbols_to_exit:
            self.execute_exit(symbol, reason)
    
    
    def run(self, scan_interval_seconds: int = 60):
        """
        Main bot loop
        
        Args:
            scan_interval_seconds: How often to scan (default 60 seconds)
        """
        logger.info("="*80)
        logger.info("🚀 VELOCITY + ACCELERATION BOT STARTING")
        logger.info("="*80)
        
        # Load universe
        self.load_universe()
        
        # Get account info
        self.get_account_info()
        
        try:
            while True:
                # Check if market is open
                clock = self.api.get_clock()
                
                if clock.is_open:
                    # Manage existing positions first
                    self.manage_positions()
                    
                    # Scan for new opportunities
                    self.scan_and_trade()
                    
                    logger.info(f"⏰ Next scan in {scan_interval_seconds} seconds...")
                    time.sleep(scan_interval_seconds)
                else:
                    next_open = clock.next_open.timestamp()
                    now = datetime.now().timestamp()
                    sleep_time = max(60, next_open - now)
                    logger.info(f"🌙 Market closed. Next open: {clock.next_open}. Sleeping...")
                    time.sleep(min(sleep_time, 300))  # Check every 5 min max
                    
        except KeyboardInterrupt:
            logger.info("⚠️  Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
        finally:
            logger.info("🛑 Bot shutting down")
            # Close all positions if desired
            # self.close_all_positions()


def main():
    """Entry point"""
    
    # Initialize bot in paper trading mode
    bot = VelocityAccelerationBot(paper_trading=True)
    
    # Run the bot (scans every 60 seconds)
    bot.run(scan_interval_seconds=60)


if __name__ == "__main__":
    main()