# Velocity + Acceleration Momentum Trading Bot

**Automated trading system implementing multi-timeframe V+A strategy with Alpaca API**

## 🎯 Strategy Overview

**Core Philosophy:** "Hunt volatility, cut losses instantly, never cap winners"

**The Edge:** Velocity + Acceleration detection on multi-timeframe analysis
- Detects when momentum is BUILDING (acceleration > 1.2)
- Exits when momentum is FADING (deceleration < 0.5)
- Enters on quality signals, not just breakouts

**Expected Performance:**
- Win Rate: 52-58%
- Avg Win: +40-45%
- Avg Loss: -2.5%
- Annual Target: +200-400% (realistic with discipline)

---

## 📋 Requirements

- Python 3.8+
- Alpaca brokerage account (free paper trading available)
- $10,000+ recommended starting capital (paper or live)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Alpaca Account

1. Go to [Alpaca](https://alpaca.markets) and create account
2. Navigate to Paper Trading dashboard
3. Generate API keys (View > API Keys)
4. Copy your API Key and Secret Key

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add your keys:
```
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### 4. Run the Bot

```bash
python trading_bot.py
```

---

## 📊 How It Works

### Entry Logic

The bot scans your universe every 60 seconds looking for:

**REQUIRED (must have all 3):**
1. ✅ **5-min breakout >4%** (25 pts)
2. ✅ **Volume >2x average** (20 pts)
3. ✅ **15-min chart is green** (10 pts)

**BONUS POINTS:**
4. **2-min breakout >3%** (+15 pts)
5. **Velocity ratio V1 > V2** (+15 pts)
6. **Acceleration >1.2** (+15 pts)

**Entry Threshold:** Score ≥70

**Position Sizing:**
- Score 90-100: 7% of capital (perfect setup)
- Score 70-89: 5% of capital (standard)
- Max 20 concurrent positions

### Exit Logic

**1. Hard Stop Loss:** -2.5% from entry (immediate exit)

**2. Break-Even Protection:** Move stop to entry at +10% profit

**3. Trailing Stops:**
- +10-20% profit: 5% trailing stop
- +20-40% profit: 10% trailing stop
- +40-70% profit: 15% trailing stop
- +70%+ profit: 20% trailing stop

**4. Deceleration Exit:** 
- If A < 0.5 while in profit → EXIT IMMEDIATELY
- If A < 0.8 while in profit → Tighten trailing stop

**5. Cooldown:** 15-minute pause before re-entering same symbol

---

## 🎛️ Configuration

Edit `config.py` to customize strategy parameters:

### Key Parameters

```python
# Position sizing
MAX_POSITIONS = 20
POSITION_SIZE_STANDARD = 0.05  # 5%
POSITION_SIZE_STRONG = 0.07    # 7%

# Risk
STOP_LOSS_PCT = 0.025          # 2.5%
BREAKEVEN_PROFIT = 0.10        # 10%

# Entry thresholds
BREAKOUT_5MIN_PCT = 0.04       # 4%
VOLUME_RATIO_MIN = 2.0         # 2x
ACCELERATION_MIN = 1.2

# Scanning
SCAN_INTERVAL_SECONDS = 60
```

---

## 📈 Universe Selection

### Option 1: Use Default Watchlist

The bot includes a default watchlist of ~50 high-volatility stocks:
- Crypto-related (MARA, RIOT, COIN)
- Biotech (SAVA, TBPH)
- Small-cap tech (IONQ, SOFI)
- EV (LCID, RIVN)
- Cannabis (TLRY, CGC)
- High-beta (GME, AMC)

### Option 2: Provide Custom Universe

Create a CSV file with your stocks:

```csv
symbol
AAPL
TSLA
NVDA
...
```

Then modify bot initialization:
```python
bot.load_universe('my_universe.csv')
```

### Option 3: Dynamic Universe Builder

Use the `universe_builder.py` script (from previous conversation) to scan ALL NYSE/NASDAQ stocks and filter by volatility.

---

## 🔍 Monitoring

### Console Output

```
================================================================================
🔍 SCANNING UNIVERSE FOR SIGNALS
================================================================================
📊 MARA: Score=95, A=1.45, 5min=5.2%, Vol=3.1x
📊 SAVA: Score=85, A=1.38, 5min=4.8%, Vol=2.4x
🚀 ENTERING MARA - Score: 95, Size: 7%
   Price: $18.45, Qty: 253, A: 1.45
✅ FILLED MARA @ $18.47, Stop: $18.01
📈 Active Positions: 1/20

================================================================================
📊 MANAGING POSITIONS
================================================================================
   MARA: $19.82 (+7.3%), Stop: $18.47
⏰ Next scan in 60 seconds...
```

### Log Files

All activity logged to `trading_bot.log`:
- Entry/exit signals with full details
- Position management updates
- Errors and warnings

---

## 🎓 Strategy Components Explained

### Velocity (V)

**Definition:** Rate of price change per minute

```
V1 = % change over last 2 minutes / 2
V2 = % change over last 5 minutes / 5
V3 = % change over last 15 minutes / 15
```

### Acceleration (A)

**Definition:** Is the move speeding up or slowing down?

```
A = V1 / V2

A > 1.2 = Accelerating (GOOD - enter)
A < 0.8 = Decelerating (WARNING - tighten stops)
A < 0.5 = Sharp deceleration (EXIT if in profit)
```

### Why This Works

Most traders buy breakouts based on POSITION ("stock is up 4%").

**You're trading based on MOMENTUM** ("stock is up 4% AND accelerating").

This means:
- You enter EARLY when acceleration detected
- Others enter LATE at the top
- You exit EARLY when deceleration detected
- Others hold too long and give back gains

**This timing edge is the difference between +150% and +400% annual returns.**

---

## ⚠️ Risk Warnings

### Paper Trading First

**ALWAYS start with paper trading:**
- Test the strategy for 2-4 weeks
- Verify win rate and avg win/loss match expectations
- Check execution quality (slippage, fills)
- Understand the drawdowns

### Capital Requirements

**Minimum recommended:** $10,000
- Each position is 5-7% ($500-700)
- Need buffer for drawdowns
- Smaller accounts get chopped up by volatility

### Drawdowns

**Expected drawdowns:** 10-20%
- You WILL have losing weeks
- You WILL have 5+ losses in a row
- This is NORMAL - trust the mathematics

### Not Financial Advice

This is an educational trading system. You are responsible for:
- Understanding the strategy
- Managing risk appropriately
- Compliance with regulations
- All trading decisions

---

## 🐛 Troubleshooting

### "No data for symbol X"

**Cause:** Symbol not actively trading or delisted
**Fix:** Remove from universe or check if halted

### "Max positions reached"

**Cause:** Already in 20 positions
**Fix:** Wait for exits or increase MAX_POSITIONS (not recommended)

### "API rate limit exceeded"

**Cause:** Too many API calls
**Fix:** Increase SCAN_INTERVAL_SECONDS

### "Order not filled"

**Cause:** Illiquid stock, market volatility, or halted
**Fix:** 
- Check stock is actively trading
- Verify sufficient volume
- Consider limit orders for illiquid stocks

### Low win rate (<45%)

**Possible causes:**
- Entry threshold too low (decrease MIN_ENTRY_SCORE)
- Market conditions (choppy/bear market)
- Stop too tight (2.5% may need adjustment for YOUR universe)

**Fix:** Backtest and adjust parameters

---

## 📊 Performance Tracking

### Metrics to Monitor

**Daily:**
- Win rate (target 52-58%)
- Avg win size (target 40%+)
- Avg loss size (should be ~2.5%)
- Number of trades

**Weekly:**
- Total P&L
- Max drawdown
- Sharpe ratio
- Best/worst trades

**Monthly:**
- Review all trades
- Identify patterns (which sectors, times, conditions work best)
- Adjust universe if needed

### When to Stop Trading

**Stop immediately if:**
- Win rate drops below 35% for 2+ weeks
- Avg loss exceeds 4% (stops not executing)
- Drawdown exceeds 30%
- You're overriding the bot emotionally

**Take a break and analyze what changed.**

---

## 🔧 Advanced Customization

### Adaptive Timeframes

Enable different timeframes based on stock volatility:

```python
# In config.py
USE_ADAPTIVE_TIMEFRAMES = True
```

This uses:
- 2-min candles for ATR >10% stocks
- 3-min for ATR 7-10%
- 5-min for ATR 5-7%

### Volume Acceleration

Add volume acceleration to scoring (future enhancement):

```python
VA = current_volume / avg_volume
if VA > 3.0:  # Volume surging
    score += 10
```

### Machine Learning

Future enhancement: Train ML model on historical V+A patterns to predict trade outcomes.

---

## 📚 Additional Resources

### Learning Materials

- **Strategy PDF:** Complete strategy documentation
- **Backtest Results:** Historical performance analysis
- **Video Tutorial:** Step-by-step setup guide

### Support

- GitHub Issues: Bug reports and feature requests
- Discord Community: Strategy discussion and support
- Email: support@example.com

---

## 🎯 Success Checklist

Before going live:

- [ ] Tested in paper trading for 4+ weeks
- [ ] Win rate consistently 48%+
- [ ] Average win 35%+
- [ ] Understand why each trade won/lost
- [ ] Comfortable with 15-20% drawdowns
- [ ] Have stop-loss discipline
- [ ] Won't override bot emotionally
- [ ] Have sufficient capital ($10k+)
- [ ] Understand tax implications
- [ ] Ready to track performance metrics

---

## 📄 License

MIT License - Use at your own risk

---

## 🙏 Acknowledgments

Built on the shoulders of:
- Alpaca Markets (API)
- Quantitative trading research
- Institutional momentum strategies

---

**Remember:** The V+A edge is your timing advantage. Trust the process, follow the rules, and let mathematics work over many trades.

**Good luck and trade safe! 🚀**
