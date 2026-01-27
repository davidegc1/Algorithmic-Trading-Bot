"""
UTILITY FUNCTIONS
Analysis, backtesting, and helper tools
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json


class PerformanceAnalyzer:
    """Analyze trading performance"""
    
    def __init__(self, trades_file: str = 'trades.json'):
        """
        Initialize analyzer
        
        Args:
            trades_file: Path to trades log file
        """
        self.trades_file = trades_file
        self.trades = self.load_trades()
    
    def load_trades(self) -> List[Dict]:
        """Load trades from file"""
        try:
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {}
        
        df = pd.DataFrame(self.trades)
        
        # Basic metrics
        total_trades = len(df)
        winners = df[df['pnl_pct'] > 0]
        losers = df[df['pnl_pct'] <= 0]
        
        win_rate = len(winners) / total_trades if total_trades > 0 else 0
        avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
        
        # Profit factor
        total_wins = winners['pnl_dollar'].sum() if len(winners) > 0 else 0
        total_losses = abs(losers['pnl_dollar'].sum()) if len(losers) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        # Max drawdown
        df['cumulative'] = df['pnl_dollar'].cumsum()
        df['running_max'] = df['cumulative'].cumsum().expanding().max()
        df['drawdown'] = df['cumulative'] - df['running_max']
        max_drawdown = df['drawdown'].min()
        
        return {
            'total_trades': total_trades,
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': win_rate * 100,
            'avg_win_pct': avg_win * 100,
            'avg_loss_pct': avg_loss * 100,
            'profit_factor': profit_factor,
            'expectancy_pct': expectancy * 100,
            'total_pnl': df['pnl_dollar'].sum(),
            'max_drawdown': max_drawdown,
            'best_trade': df['pnl_pct'].max() * 100,
            'worst_trade': df['pnl_pct'].min() * 100
        }
    
    def print_summary(self):
        """Print performance summary"""
        metrics = self.calculate_metrics()
        
        if not metrics:
            print("No trades to analyze")
            return
        
        print("="*80)
        print("PERFORMANCE SUMMARY")
        print("="*80)
        print(f"Total Trades:     {metrics['total_trades']}")
        print(f"Winners:          {metrics['winners']} ({metrics['win_rate']:.1f}%)")
        print(f"Losers:           {metrics['losers']}")
        print()
        print(f"Average Win:      {metrics['avg_win_pct']:+.2f}%")
        print(f"Average Loss:     {metrics['avg_loss_pct']:+.2f}%")
        print(f"Expectancy:       {metrics['expectancy_pct']:+.2f}% per trade")
        print()
        print(f"Profit Factor:    {metrics['profit_factor']:.2f}")
        print(f"Total P&L:        ${metrics['total_pnl']:,.2f}")
        print(f"Max Drawdown:     ${metrics['max_drawdown']:,.2f}")
        print()
        print(f"Best Trade:       {metrics['best_trade']:+.2f}%")
        print(f"Worst Trade:      {metrics['worst_trade']:+.2f}%")
        print("="*80)
    
    def analyze_by_signal_score(self) -> pd.DataFrame:
        """Analyze performance by signal score"""
        if not self.trades:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.trades)
        
        # Create score bins
        df['score_bin'] = pd.cut(
            df['signal_score'],
            bins=[0, 70, 80, 90, 100],
            labels=['70-79', '80-89', '90-99', '100']
        )
        
        # Group by score
        grouped = df.groupby('score_bin').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
        })
        
        grouped.columns = ['Count', 'Avg P&L %', 'Win Rate %']
        
        return grouped
    
    def analyze_by_acceleration(self) -> pd.DataFrame:
        """Analyze performance by acceleration levels"""
        if not self.trades:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.trades)
        
        # Create acceleration bins
        df['accel_bin'] = pd.cut(
            df['acceleration'],
            bins=[0, 1.0, 1.2, 1.5, 10],
            labels=['<1.0', '1.0-1.2', '1.2-1.5', '>1.5']
        )
        
        # Group by acceleration
        grouped = df.groupby('accel_bin').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
        })
        
        grouped.columns = ['Count', 'Avg P&L %', 'Win Rate %']
        
        return grouped


class TradeLogger:
    """Log all trades for analysis"""
    
    def __init__(self, filepath: str = 'trades.json'):
        self.filepath = filepath
        self.trades = []
        self.load()
    
    def load(self):
        """Load existing trades"""
        try:
            with open(self.filepath, 'r') as f:
                self.trades = json.load(f)
        except FileNotFoundError:
            self.trades = []
    
    def log_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        entry_time: datetime,
        exit_time: datetime,
        signal_score: int,
        acceleration: float,
        exit_reason: str
    ):
        """Log a completed trade"""
        
        pnl_pct = (exit_price - entry_price) / entry_price
        pnl_dollar = (exit_price - entry_price) * quantity
        hold_time = (exit_time - entry_time).total_seconds() / 3600  # hours
        
        trade = {
            'symbol': symbol,
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'hold_time_hours': hold_time,
            'signal_score': signal_score,
            'acceleration': acceleration,
            'exit_reason': exit_reason
        }
        
        self.trades.append(trade)
        self.save()
    
    def save(self):
        """Save trades to file"""
        with open(self.filepath, 'w') as f:
            json.dump(self.trades, f, indent=2)


def calculate_atr(bars: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate Average True Range
    
    Args:
        bars: DataFrame with high, low, close columns
        period: ATR period (default 14)
        
    Returns:
        ATR value as percentage of price
    """
    if len(bars) < period:
        return 0
    
    high = bars['high']
    low = bars['low']
    close = bars['close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR
    atr = tr.rolling(window=period).mean().iloc[-1]
    
    # Return as percentage
    current_price = close.iloc[-1]
    return (atr / current_price) if current_price > 0 else 0


def filter_by_atr(
    symbols: List[str],
    min_atr_pct: float = 0.05,
    api = None
) -> List[str]:
    """
    Filter symbols by ATR requirement
    
    Args:
        symbols: List of symbols to filter
        min_atr_pct: Minimum ATR percentage (default 5%)
        api: Alpaca API instance
        
    Returns:
        Filtered list of symbols meeting ATR requirement
    """
    if not api:
        return symbols
    
    filtered = []
    
    for symbol in symbols:
        try:
            # Get daily bars
            bars = api.get_bars(symbol, '1D', limit=30).df
            
            if bars.empty:
                continue
            
            # Calculate ATR
            atr_pct = calculate_atr(bars)
            
            if atr_pct >= min_atr_pct:
                filtered.append(symbol)
                print(f"✅ {symbol}: ATR = {atr_pct*100:.1f}%")
            else:
                print(f"❌ {symbol}: ATR = {atr_pct*100:.1f}% (too low)")
                
        except Exception as e:
            print(f"⚠️  {symbol}: Error - {e}")
            continue
    
    print(f"\n📊 Filtered: {len(filtered)}/{len(symbols)} stocks meet ATR >{min_atr_pct*100}%")
    return filtered


def validate_strategy_parameters():
    """Validate that strategy parameters make sense"""
    from config import (
        STOP_LOSS_PCT, BREAKEVEN_PROFIT, TRAILING_STOPS,
        BREAKOUT_5MIN_PCT, VOLUME_RATIO_MIN, ACCELERATION_MIN,
        MIN_ENTRY_SCORE, MAX_POSITIONS, POSITION_SIZE_STANDARD
    )
    
    issues = []
    
    # Check stop loss is reasonable
    if STOP_LOSS_PCT > 0.05:
        issues.append(f"⚠️  Stop loss {STOP_LOSS_PCT*100}% seems high (recommend <5%)")
    
    # Check breakeven makes sense
    if BREAKEVEN_PROFIT <= STOP_LOSS_PCT:
        issues.append(f"⚠️  Breakeven profit ({BREAKEVEN_PROFIT*100}%) should be higher than stop loss")
    
    # Check trailing stops
    for profit, trail in TRAILING_STOPS.items():
        if trail >= profit:
            issues.append(f"⚠️  Trailing stop {trail*100}% >= profit level {profit*100}%")
    
    # Check position sizing
    total_risk = MAX_POSITIONS * POSITION_SIZE_STANDARD * STOP_LOSS_PCT
    if total_risk > 0.15:
        issues.append(f"⚠️  Max portfolio risk {total_risk*100:.1f}% is high (recommend <15%)")
    
    # Check acceleration threshold
    if ACCELERATION_MIN < 1.0:
        issues.append(f"⚠️  Acceleration {ACCELERATION_MIN} < 1.0 means decelerating (should be >1.0)")
    
    if issues:
        print("="*80)
        print("CONFIGURATION WARNINGS")
        print("="*80)
        for issue in issues:
            print(issue)
        print("="*80)
        return False
    else:
        print("✅ Configuration validated - all parameters look good")
        return True


if __name__ == "__main__":
    # Example usage
    
    # Validate configuration
    print("Validating strategy parameters...")
    validate_strategy_parameters()
    
    # Analyze performance
    print("\nAnalyzing performance...")
    analyzer = PerformanceAnalyzer()
    analyzer.print_summary()
    
    print("\nPerformance by Signal Score:")
    print(analyzer.analyze_by_signal_score())
    
    print("\nPerformance by Acceleration:")
    print(analyzer.analyze_by_acceleration())
