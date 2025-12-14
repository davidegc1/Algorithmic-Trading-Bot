"""
Advanced High Volatility Stock Scanner with Multiple Data Sources
Includes real-time screening and technical indicators
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional
import time
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AdvancedVolatilityScanner:
    """Advanced scanner with multiple strategies and data sources"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Load from environment or use provided key
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        self.finviz_base = "https://finviz.com/screener.ashx"
        
    def get_finviz_screener(
        self,
        min_price: float = 1.0,
        max_price: float = 10.0,
        min_volume: int = 1_000_000,
        min_change: float = 5.0
    ) -> List[str]:
        """
        Get stocks from Finviz screener
        Note: This is a simplified version. For production, consider using finvizfinance library
        """
        # For now, return expanded universe
        # In production, you'd scrape or use Finviz API
        return self.get_expanded_universe()
    
    def get_expanded_universe(self) -> List[str]:
        """Expanded universe of volatile stocks across sectors"""
        
        biotech = [
            'SAVA', 'TBPH', 'APLD', 'DRUG', 'ABOS', 'BDTX', 'CGEM',
            'DMAC', 'FBRX', 'IMMP', 'IRWD', 'MDGL', 'PRAX', 'VTRS',
            'SRPT', 'BMRN', 'FOLD', 'RGNX', 'IONS', 'ALNY', 'VRTX',
            'CRSP', 'EDIT', 'NTLA', 'BEAM', 'TGTX', 'KPTI'
        ]
        
        small_tech = [
            'IONQ', 'QUBT', 'RGTI', 'SOFI', 'UPST', 'HOOD', 'OPEN', 'RKLB',
            'ACHR', 'JOBY', 'LILM', 'EVTL', 'BIRD', 'PATH',
            'SOUN', 'BBAI', 'BKSY', 'SPIR', 'ASTS', 'LUNR', 'SPCE',
            'ASTR', 'MNTS', 'PLTR', 'SNOW', 'RBLX', 'U', 'DDOG'
        ]
        
        crypto_related = [
            'MARA', 'RIOT', 'CLSK', 'CIFR', 'BITF', 'HUT', 'BTBT', 'COIN',
            'MSTR', 'SOS', 'CAN', 'BTCS', 'GREE', 'WULF', 'IREN', 'CORZ',
            'ANY', 'ARBK'
        ]
        
        ev_battery = [
            'LCID', 'RIVN', 'WKHS', 'NKLA',
            'CHPT', 'BLNK', 'EVGO', 'PLUG',
            'FCEL', 'BLDP', 'BE', 'QS', 'SES', 'SLDP', 'MVST'
        ]
        
        cannabis = [
            'TLRY', 'CGC', 'SNDL', 'ACB', 'CRON', 'OGI',
            'CURLF', 'GTBIF', 'TCNNF', 'CRLBF', 'GRWG', 'SMG'
        ]
        
        meme_high_beta = [
            'GME', 'AMC', 'BBBY', 'KOSS', 'CLOV',
            'SKLZ', 'UWMC', 'RKT', 'CLNE', 'WKHS', 'BB', 'NOK', 'SNDL'
        ]
        
        penny_tech = [
            'MVIS', 'LAZR', 'OUST', 'INVZ', 'AEYE', 'LIDR', 'KOPN',
            'WIMI', 'GOTU', 'BTCT', 'NCTY', 'TIGR', 'FUBO', 'TALK'
        ]
        
        semiconductors = [
            'AMD', 'NVDA', 'SMCI', 'AVGO', 'ARM', 'MRVL', 'ON', 'MU',
            'AMAT', 'LRCX', 'KLAC', 'MPWR', 'WOLF', 'CRUS', 'SYNA', 'ALGM'
        ]
        
        recent_ipos = [
            'ARM', 'RDDT', 'KVUE', 'FBIN', 'CART', 'MNDY', 'IOT', 'CWAN',
            'DOCN', 'BILL', 'S', 'DASH', 'ABNB', 'COIN', 'RBLX'
        ]
        
        # Combine all
        all_tickers = list(set(
            biotech + small_tech + crypto_related + ev_battery + 
            cannabis + meme_high_beta + penny_tech + semiconductors + recent_ipos
        ))
        
        return all_tickers
    
    def get_real_time_metrics(self, ticker: str) -> Dict:
        """Get comprehensive real-time metrics for a stock"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get real-time quote
            info = stock.info
            
            # Historical data for calculations
            hist = stock.history(period='3mo', interval='1d')
            
            if hist.empty or len(hist) < 20:
                return None
            
            # Recent minute data for intraday volatility
            try:
                intraday = stock.history(period='1d', interval='1m')
            except:
                intraday = pd.DataFrame()
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns = hist['Close'].pct_change().dropna()
            
            # Multi-timeframe volatility calculations
            # Daily volatility (last 1 day - really just the last close change)
            if len(returns) >= 1:
                daily_vol = abs(returns.iloc[-1]) * 100
            else:
                daily_vol = 0
            
            # Weekly volatility (last 5 days annualized)
            if len(returns) >= 5:
                weekly_returns = returns.tail(5)
                weekly_vol = weekly_returns.std() * np.sqrt(252) * 100
            else:
                weekly_vol = None
            
            # Monthly volatility (last 20 days annualized)
            if len(returns) >= 20:
                monthly_returns = returns.tail(20)
                monthly_vol = monthly_returns.std() * np.sqrt(252) * 100
            else:
                monthly_vol = None
            
            # Quarterly volatility (last 60 days annualized)
            if len(returns) >= 60:
                quarterly_returns = returns.tail(60)
                quarterly_vol = quarterly_returns.std() * np.sqrt(252) * 100
            else:
                quarterly_vol = None
            
            # Annual volatility (full history - standard metric)
            hist_vol = returns.std() * np.sqrt(252) * 100
            
            # Volatility trend analysis
            if weekly_vol and monthly_vol and quarterly_vol:
                if weekly_vol > monthly_vol > quarterly_vol:
                    vol_regime = "Accelerating"  # Expanding volatility
                elif weekly_vol < monthly_vol < quarterly_vol:
                    vol_regime = "Decelerating"  # Contracting volatility
                else:
                    vol_regime = "Mixed"
            else:
                vol_regime = "Unknown"
            
            # Recent volatility (last 10 days for comparison)
            recent_vol = returns.tail(10).std() * np.sqrt(252) * 100
            
            # ATR
            high_low = hist['High'] - hist['Low']
            high_close = np.abs(hist['High'] - hist['Close'].shift())
            low_close = np.abs(hist['Low'] - hist['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr_14 = true_range.rolling(14).mean().iloc[-1]
            atr_pct = (atr_14 / current_price) * 100
            
            # Intraday volatility
            if not intraday.empty and len(intraday) > 10:
                intraday_returns = intraday['Close'].pct_change().dropna()
                intraday_vol = intraday_returns.std() * 100
            else:
                intraday_vol = None
            
            # Price action
            day_change = ((current_price - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1]) * 100
            day_high = hist['High'].iloc[-1]
            day_low = hist['Low'].iloc[-1]
            day_range = ((day_high - day_low) / hist['Open'].iloc[-1]) * 100
            
            # Moving averages
            ma_20 = hist['Close'].rolling(20).mean().iloc[-1]
            ma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
            
            # Distance from MAs
            dist_from_ma20 = ((current_price - ma_20) / ma_20) * 100
            dist_from_ma50 = ((current_price - ma_50) / ma_50) * 100 if ma_50 else None
            
            # Volume analysis
            avg_vol_20 = hist['Volume'].tail(20).mean()
            current_vol = hist['Volume'].iloc[-1]
            vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 0
            
            # Recent performance
            week_change = ((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100 if len(hist) >= 5 else None
            month_change = ((current_price - hist['Close'].iloc[-20]) / hist['Close'].iloc[-20]) * 100 if len(hist) >= 20 else None
            
            # Volatility trend (increasing or decreasing)
            vol_10d = returns.tail(10).std() * np.sqrt(252) * 100
            vol_30d = returns.tail(30).std() * np.sqrt(252) * 100
            vol_trend = "Increasing" if vol_10d > vol_30d else "Decreasing"
            
            # Additional info
            beta = info.get('beta', None)
            market_cap = info.get('marketCap', 0)
            short_ratio = info.get('shortRatio', None)
            fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
            fifty_two_week_low = info.get('fiftyTwoWeekLow', None)
            
            # Distance from 52-week high/low
            if fifty_two_week_high:
                dist_from_52w_high = ((current_price - fifty_two_week_high) / fifty_two_week_high) * 100
            else:
                dist_from_52w_high = None
                
            if fifty_two_week_low:
                dist_from_52w_low = ((current_price - fifty_two_week_low) / fifty_two_week_low) * 100
            else:
                dist_from_52w_low = None
            
            return {
                'ticker': ticker,
                'price': round(current_price, 2),
                'day_change_%': round(day_change, 2),
                'day_range_%': round(day_range, 2),
                'week_change_%': round(week_change, 2) if week_change else None,
                'month_change_%': round(month_change, 2) if month_change else None,
                
                # Multi-timeframe volatility
                'daily_vol_%': round(daily_vol, 2),
                'weekly_vol_%': round(weekly_vol, 2) if weekly_vol else None,
                'monthly_vol_%': round(monthly_vol, 2) if monthly_vol else None,
                'quarterly_vol_%': round(quarterly_vol, 2) if quarterly_vol else None,
                'annual_vol_%': round(hist_vol, 2),
                
                'recent_vol_%': round(recent_vol, 2),
                'vol_regime': vol_regime,
                'vol_trend': vol_trend,
                
                'atr': round(atr_14, 2),
                'atr_%': round(atr_pct, 2),
                'intraday_vol_%': round(intraday_vol, 2) if intraday_vol else None,
                'volume': int(current_vol),
                'avg_volume': int(avg_vol_20),
                'vol_ratio': round(vol_ratio, 2),
                'beta': round(beta, 2) if beta else None,
                'market_cap_$M': round(market_cap / 1_000_000, 1) if market_cap else None,
                'short_ratio': round(short_ratio, 2) if short_ratio else None,
                'dist_from_ma20_%': round(dist_from_ma20, 2),
                'dist_from_ma50_%': round(dist_from_ma50, 2) if dist_from_ma50 else None,
                'dist_from_52w_high_%': round(dist_from_52w_high, 2) if dist_from_52w_high else None,
                'dist_from_52w_low_%': round(dist_from_52w_low, 2) if dist_from_52w_low else None,
                'exchange': info.get('exchange', 'Unknown')
            }
            
        except Exception as e:
            print(f"Error with {ticker}: {str(e)}")
            return None
    
    def scan_market(self, custom_tickers: List[str] = None) -> pd.DataFrame:
        """Scan the market for volatile opportunities"""
        
        if custom_tickers:
            tickers = custom_tickers
        else:
            tickers = self.get_expanded_universe()
        
        print(f"Scanning {len(tickers)} stocks...")
        print("This will take 3-5 minutes for comprehensive analysis\n")
        
        results = []
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Processing {ticker}...", end='\r')
            
            metrics = self.get_real_time_metrics(ticker)
            if metrics:
                results.append(metrics)
            
            # Rate limiting
            if i % 10 == 0:
                time.sleep(2)
        
        print("\n\nScan complete!")
        
        if not results:
            return pd.DataFrame()
        
        return pd.DataFrame(results)
    
    def find_breakout_candidates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Find stocks breaking out of consolidation with volume"""
        breakouts = df[
            (df['day_change_%'].abs() > 5) &
            (df['vol_ratio'] > 1.5) &
            (df['atr_%'] > 3)
        ].copy()
        
        breakouts['breakout_score'] = (
            breakouts['day_change_%'].abs() * 0.3 +
            breakouts['vol_ratio'] * 20 * 0.3 +
            breakouts['atr_%'] * 10 * 0.4
        )
        
        return breakouts.sort_values('breakout_score', ascending=False)
    
    def find_momentum_plays(self, df: pd.DataFrame) -> pd.DataFrame:
        """Find stocks with strong momentum and increasing volatility"""
        momentum = df[
            (df['week_change_%'] > 10) &
            (df['vol_regime'] == 'Accelerating') &
            (df['vol_ratio'] > 1.2)
        ].copy()
        
        momentum['momentum_score'] = (
            momentum['week_change_%'] * 0.4 +
            momentum['weekly_vol_%'].fillna(momentum['annual_vol_%']) * 0.3 +
            momentum['vol_ratio'] * 30 * 0.3
        )
        
        return momentum.sort_values('momentum_score', ascending=False)
    
    def find_high_risk_high_reward(self, df: pd.DataFrame) -> pd.DataFrame:
        """Find the most volatile, aggressive opportunities"""
        high_risk = df[
            (df['price'] >= 1) &
            (df['price'] <= 10) &
            (df['annual_vol_%'] > 70) &
            (df['atr_%'] > 4) &
            (df['avg_volume'] > 1_000_000) &
            (df['market_cap_$M'] < 2000)
        ].copy()
        
        high_risk['aggression_score'] = (
            high_risk['annual_vol_%'] * 0.35 +
            high_risk['monthly_vol_%'].fillna(high_risk['annual_vol_%']) * 0.35 +
            high_risk['atr_%'] * 5 * 0.3
        )
        
        return high_risk.sort_values('aggression_score', ascending=False)


def run_comprehensive_scan():
    """Run comprehensive scan with all strategies"""
    
    scanner = AdvancedVolatilityScanner()
    
    print(f"\n{'='*80}")
    print("COMPREHENSIVE VOLATILE STOCK SCANNER")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Scan market
    df = scanner.scan_market()
    
    if df.empty:
        print("No data retrieved")
        return
    
    # Strategy 1: High Risk High Reward
    print(f"\n{'='*80}")
    print("STRATEGY 1: HIGH RISK / HIGH REWARD")
    print("(70%+ volatility, 4%+ ATR, $1-10 price range)")
    print(f"{'='*80}")
    
    high_risk = scanner.find_high_risk_high_reward(df)
    if not high_risk.empty:
        display_cols = ['ticker', 'price', 'day_change_%', 'weekly_vol_%', 'monthly_vol_%', 
                       'annual_vol_%', 'vol_regime', 'atr_%', 'aggression_score', 'market_cap_$M']
        print(high_risk.head(15)[display_cols].to_string(index=False))
    else:
        print("No stocks matching criteria")
    
    # Strategy 2: Breakout Candidates
    print(f"\n{'='*80}")
    print("STRATEGY 2: BREAKOUT CANDIDATES")
    print("(5%+ move today with volume surge)")
    print(f"{'='*80}")
    
    breakouts = scanner.find_breakout_candidates(df)
    if not breakouts.empty:
        display_cols = ['ticker', 'price', 'day_change_%', 'vol_ratio', 
                       'atr_%', 'breakout_score', 'dist_from_ma20_%']
        print(breakouts.head(15)[display_cols].to_string(index=False))
    else:
        print("No breakouts detected")
    
    # Strategy 3: Momentum Plays
    print(f"\n{'='*80}")
    print("STRATEGY 3: MOMENTUM PLAYS")
    print("(10%+ weekly gain, increasing volatility)")
    print(f"{'='*80}")
    
    momentum = scanner.find_momentum_plays(df)
    if not momentum.empty:
        display_cols = ['ticker', 'price', 'week_change_%', 'weekly_vol_%', 'monthly_vol_%',
                       'vol_regime', 'momentum_score', 'dist_from_ma50_%']
        print(momentum.head(15)[display_cols].to_string(index=False))
    else:
        print("No momentum plays found")
    
    # Top volume surges
    print(f"\n{'='*80}")
    print("VOLUME SURGE ALERTS (Top 15)")
    print(f"{'='*80}")
    
    vol_surge = df.nlargest(15, 'vol_ratio')[
        ['ticker', 'price', 'day_change_%', 'volume', 'vol_ratio', 
         'monthly_vol_%', 'annual_vol_%', 'vol_regime', 'market_cap_$M']
    ]
    print(vol_surge.to_string(index=False))
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    df.to_csv(f'/home/claude/volatile_scan_{timestamp}.csv', index=False)
    print(f"\n\nFull results saved to: volatile_scan_{timestamp}.csv")
    
    if not high_risk.empty:
        high_risk.to_csv(f'/home/claude/high_risk_plays_{timestamp}.csv', index=False)
        print(f"High risk plays saved to: high_risk_plays_{timestamp}.csv")
    
    # Summary stats
    print(f"\n{'='*80}")
    print("MARKET SUMMARY")
    print(f"{'='*80}")
    print(f"Total stocks analyzed: {len(df)}")
    print(f"Average annual volatility: {df['annual_vol_%'].mean():.1f}%")
    print(f"Average monthly volatility: {df['monthly_vol_%'].mean():.1f}%")
    print(f"Highest volatility: {df['annual_vol_%'].max():.1f}% ({df.loc[df['annual_vol_%'].idxmax(), 'ticker']})")
    print(f"Stocks >100% volatility: {len(df[df['annual_vol_%'] > 100])}")
    print(f"Stocks with 2x+ volume: {len(df[df['vol_ratio'] >= 2])}")
    print(f"Accelerating volatility: {len(df[df['vol_regime'] == 'Accelerating'])}")
    print(f"Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}\n")


if __name__ == "__main__":
    run_comprehensive_scan()
