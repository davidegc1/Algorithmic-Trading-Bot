"""
TRADE ANALYSIS & REPORTING
Detailed analysis of all trades with visualizations
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import os


class TradeAnalyzer:
    """Comprehensive trade analysis"""
    
    def __init__(self, trades_file: str = 'trades.json'):
        self.trades_file = trades_file
        self.df = self.load_trades()
    
    def load_trades(self) -> pd.DataFrame:
        """Load trades into DataFrame"""
        if not os.path.exists(self.trades_file):
            print(f"⚠️  No trade history found at {self.trades_file}")
            return pd.DataFrame()
        
        with open(self.trades_file, 'r') as f:
            trades = json.load(f)
        
        if not trades:
            print("⚠️  No trades in history")
            return pd.DataFrame()
        
        df = pd.DataFrame(trades)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df['date'] = df['entry_time'].dt.date
        
        return df
    
    def generate_full_report(self):
        """Generate comprehensive analysis report"""
        if self.df.empty:
            print("No trades to analyze")
            return
        
        print("="*80)
        print("COMPLETE TRADE ANALYSIS REPORT")
        print("="*80)
        print()
        
        self.overall_statistics()
        print()
        self.win_loss_analysis()
        print()
        self.time_analysis()
        print()
        self.signal_quality_analysis()
        print()
        self.symbol_performance()
        print()
        self.exit_reason_analysis()
        print()
        self.daily_performance()
        print()
        self.best_worst_trades()
    
    def overall_statistics(self):
        """Overall performance metrics"""
        print("📊 OVERALL STATISTICS")
        print("-" * 80)
        
        total = len(self.df)
        winners = self.df[self.df['pnl_pct'] > 0]
        losers = self.df[self.df['pnl_pct'] <= 0]
        
        win_rate = len(winners) / total * 100 if total > 0 else 0
        avg_win = winners['pnl_pct'].mean() * 100 if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() * 100 if len(losers) > 0 else 0
        
        total_pnl = self.df['pnl_dollar'].sum()
        avg_pnl = self.df['pnl_dollar'].mean()
        
        # Profit factor
        total_wins = winners['pnl_dollar'].sum() if len(winners) > 0 else 0
        total_losses = abs(losers['pnl_dollar'].sum()) if len(losers) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Expectancy
        expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
        
        print(f"Total Trades:        {total}")
        print(f"Winners:             {len(winners)} ({win_rate:.1f}%)")
        print(f"Losers:              {len(losers)} ({100-win_rate:.1f}%)")
        print()
        print(f"Average Win:         {avg_win:+.2f}%")
        print(f"Average Loss:        {avg_loss:+.2f}%")
        print(f"Expectancy:          {expectancy:+.2f}% per trade")
        print()
        print(f"Total P&L:           ${total_pnl:,.2f}")
        print(f"Average P&L:         ${avg_pnl:,.2f}")
        print(f"Profit Factor:       {profit_factor:.2f}x")
        print()
        print(f"Best Trade:          {self.df['pnl_pct'].max()*100:+.2f}%")
        print(f"Worst Trade:         {self.df['pnl_pct'].min()*100:+.2f}%")
        print(f"Median Trade:        {self.df['pnl_pct'].median()*100:+.2f}%")
    
    def win_loss_analysis(self):
        """Detailed win/loss breakdown"""
        print("🎯 WIN/LOSS ANALYSIS")
        print("-" * 80)
        
        winners = self.df[self.df['pnl_pct'] > 0]
        losers = self.df[self.df['pnl_pct'] <= 0]
        
        # Win size distribution
        if len(winners) > 0:
            print("Winner Distribution:")
            print(f"  Small wins (0-10%):     {len(winners[winners['pnl_pct'] < 0.10])} trades")
            print(f"  Medium wins (10-30%):   {len(winners[(winners['pnl_pct'] >= 0.10) & (winners['pnl_pct'] < 0.30)])} trades")
            print(f"  Large wins (30-70%):    {len(winners[(winners['pnl_pct'] >= 0.30) & (winners['pnl_pct'] < 0.70)])} trades")
            print(f"  Moonshots (70%+):       {len(winners[winners['pnl_pct'] >= 0.70])} trades")
            print()
        
        # Loss distribution
        if len(losers) > 0:
            print("Loser Distribution:")
            print(f"  Small losses (0-2%):    {len(losers[losers['pnl_pct'] > -0.02])} trades")
            print(f"  Expected (-2 to -3%):   {len(losers[(losers['pnl_pct'] <= -0.02) & (losers['pnl_pct'] > -0.03)])} trades")
            print(f"  Large losses (-3%+):    {len(losers[losers['pnl_pct'] <= -0.03])} trades")
    
    def time_analysis(self):
        """Time-based analysis"""
        print("⏱️  TIME ANALYSIS")
        print("-" * 80)
        
        avg_hold = self.df['hold_time_hours'].mean()
        median_hold = self.df['hold_time_hours'].median()
        
        print(f"Average Hold Time:   {avg_hold:.1f} hours ({avg_hold/24:.1f} days)")
        print(f"Median Hold Time:    {median_hold:.1f} hours")
        print(f"Shortest Trade:      {self.df['hold_time_hours'].min():.1f} hours")
        print(f"Longest Trade:       {self.df['hold_time_hours'].max():.1f} hours")
        print()
        
        # Winners vs losers hold time
        winners = self.df[self.df['pnl_pct'] > 0]
        losers = self.df[self.df['pnl_pct'] <= 0]
        
        if len(winners) > 0 and len(losers) > 0:
            print(f"Avg Winner Hold:     {winners['hold_time_hours'].mean():.1f} hours")
            print(f"Avg Loser Hold:      {losers['hold_time_hours'].mean():.1f} hours")
    
    def signal_quality_analysis(self):
        """Analyze performance by signal score"""
        print("📈 SIGNAL QUALITY ANALYSIS")
        print("-" * 80)
        
        # Create score bins
        self.df['score_bin'] = pd.cut(
            self.df['signal_score'],
            bins=[0, 70, 80, 90, 100],
            labels=['70-79', '80-89', '90-99', '100']
        )
        
        grouped = self.df.groupby('score_bin', observed=True).agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
        }).round(2)
        
        grouped.columns = ['Trades', 'Avg P&L %', 'Win Rate %']
        grouped['Avg P&L %'] = grouped['Avg P&L %'] * 100
        
        print(grouped.to_string())
        print()
        print("💡 Insight: Higher scores should = better performance")
    
    def symbol_performance(self):
        """Best and worst performing symbols"""
        print("🏆 SYMBOL PERFORMANCE")
        print("-" * 80)
        
        symbol_stats = self.df.groupby('symbol').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100],
            'pnl_dollar': 'sum'
        }).round(2)
        
        symbol_stats.columns = ['Trades', 'Avg P&L %', 'Win Rate %', 'Total $']
        symbol_stats['Avg P&L %'] = symbol_stats['Avg P&L %'] * 100
        symbol_stats = symbol_stats.sort_values('Total $', ascending=False)
        
        print("Top 10 Performers:")
        print(symbol_stats.head(10).to_string())
        print()
        print("Bottom 5 Performers:")
        print(symbol_stats.tail(5).to_string())
    
    def exit_reason_analysis(self):
        """Analyze exit reasons"""
        print("🚪 EXIT REASON ANALYSIS")
        print("-" * 80)
        
        exit_stats = self.df.groupby('exit_reason').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
        }).round(2)
        
        exit_stats.columns = ['Count', 'Avg P&L %', 'Win Rate %']
        exit_stats['Avg P&L %'] = exit_stats['Avg P&L %'] * 100
        exit_stats = exit_stats.sort_values('Count', ascending=False)
        
        print(exit_stats.to_string())
        print()
        print("💡 Key Insights:")
        print("  - STOP LOSS: Should be ~100% losers at -2.5%")
        print("  - TRAILING STOP: Should be mostly winners")
        print("  - DECELERATION: Should be winners, exited early")
    
    def daily_performance(self):
        """Day-by-day performance"""
        print("📅 DAILY PERFORMANCE")
        print("-" * 80)
        
        daily = self.df.groupby('date').agg({
            'pnl_dollar': ['sum', 'count'],
            'pnl_pct': lambda x: (x > 0).sum() / len(x) * 100
        }).round(2)
        
        daily.columns = ['P&L $', 'Trades', 'Win Rate %']
        
        print(daily.to_string())
        print()
        print(f"Best Day:   {daily['P&L $'].max():+,.2f}")
        print(f"Worst Day:  {daily['P&L $'].min():+,.2f}")
        print(f"Avg Day:    {daily['P&L $'].mean():+,.2f}")
    
    def best_worst_trades(self):
        """Show best and worst individual trades"""
        print("🌟 BEST & WORST TRADES")
        print("-" * 80)
        
        print("Top 5 Winners:")
        top_5 = self.df.nlargest(5, 'pnl_pct')[['symbol', 'entry_time', 'pnl_pct', 'pnl_dollar', 'hold_time_hours', 'signal_score', 'exit_reason']]
        for idx, row in top_5.iterrows():
            print(f"  {row['symbol']}: {row['pnl_pct']*100:+.1f}% (${row['pnl_dollar']:+,.2f}) - "
                  f"Score:{row['signal_score']}, Hold:{row['hold_time_hours']:.1f}h, Exit:{row['exit_reason']}")
        
        print()
        print("Top 5 Losers:")
        bottom_5 = self.df.nsmallest(5, 'pnl_pct')[['symbol', 'entry_time', 'pnl_pct', 'pnl_dollar', 'hold_time_hours', 'signal_score', 'exit_reason']]
        for idx, row in bottom_5.iterrows():
            print(f"  {row['symbol']}: {row['pnl_pct']*100:+.1f}% (${row['pnl_dollar']:+,.2f}) - "
                  f"Score:{row['signal_score']}, Hold:{row['hold_time_hours']:.1f}h, Exit:{row['exit_reason']}")
    
    def export_to_csv(self, filename: str = 'trade_analysis.csv'):
        """Export all trades to CSV for Excel analysis"""
        if self.df.empty:
            print("No trades to export")
            return
        
        self.df.to_csv(filename, index=False)
        print(f"✅ Exported {len(self.df)} trades to {filename}")
    
    def quick_stats(self):
        """Quick one-line stats"""
        if self.df.empty:
            return "No trades yet"
        
        total = len(self.df)
        win_rate = (self.df['pnl_pct'] > 0).sum() / total * 100
        avg_win = self.df[self.df['pnl_pct'] > 0]['pnl_pct'].mean() * 100
        total_pnl = self.df['pnl_dollar'].sum()
        
        return f"{total} trades | {win_rate:.1f}% win rate | {avg_win:+.1f}% avg win | ${total_pnl:+,.2f} total"


def main():
    """Run full analysis"""
    analyzer = TradeAnalyzer('trades.json')
    
    if analyzer.df.empty:
        print("No trades found. Run the bot first to generate data!")
        return
    
    # Generate full report
    analyzer.generate_full_report()
    
    print()
    print("="*80)
    
    # Export to CSV
    export = input("\nExport to CSV for Excel analysis? (y/n): ")
    if export.lower() == 'y':
        analyzer.export_to_csv()
    
    print()
    print("✅ Analysis complete!")


if __name__ == "__main__":
    main()
