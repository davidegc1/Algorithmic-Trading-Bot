# Multi-Timeframe Volatility Trading Guide

## 🎯 Quick Reference: What Each Timeframe Means

| Timeframe | Lookback | Best For | Trading Action |
|-----------|----------|----------|----------------|
| **Daily** | 1 day | Today's action | Intraday entries/exits |
| **Weekly** | 5 days | Short-term momentum | Swing trade setups |
| **Monthly** | 20 days | Position sizing | Risk management |
| **Quarterly** | 60 days | Pattern confirmation | Trend validation |
| **Annual** | 252 days | Overall risk profile | Portfolio allocation |

---

## 🚀 Trading Strategies Using Multi-Timeframe Volatility

### **Strategy 1: Volatility Breakout Entry**

**Setup:**
```
Quarterly Vol: 80%  (baseline - stock usually calm)
Monthly Vol:   70%  (still calm)
Weekly Vol:    90%  (starting to heat up)
Daily Vol:     150% (EXPLOSION!)

Vol Regime: "Accelerating"
```

**Action:** 🚀 **ENTER NOW**
- Volatility expanding across timeframes
- Big move in progress
- Get in early before it runs

**Example Trade:**
```python
# Stock: SEMR at $11.86
# Setup detected on Monday morning
# Entry: $11.86
# Stop: $10.50 (11% stop, ~1.5x weekly vol)
# Target: $15.00 (26% gain, ~3x weekly vol)
# Risk/Reward: 1:2.4
```

---

### **Strategy 2: Volatility Compression Setup**

**Setup:**
```
Annual Vol:    150% (normally very volatile)
Quarterly Vol: 140% (still high)
Monthly Vol:   100% (cooling down)
Weekly Vol:    70%  (quiet)
Daily Vol:     40%  (dead)

Vol Regime: "Decelerating"
```

**Action:** 📋 **WATCH & WAIT**
- Stock coiling for explosive move
- Direction unknown yet
- Wait for volume spike + direction confirmation

**What to Monitor:**
- Watch for volume surge (2x+ average)
- Look for breakout above/below range
- When weekly vol > monthly vol → Entry signal

---

### **Strategy 3: Mean Reversion Trade**

**Setup:**
```
Annual Vol:    100% (baseline)
Monthly Vol:   110% (slightly elevated)
Weekly Vol:    200% (spike!)
Daily Vol:     400% (extreme spike!)

Vol Regime: "Mixed" or "Accelerating"
Price: Down 30% in 3 days
```

**Action:** 💰 **CONTRARIAN ENTRY**
- Volatility spike unsustainable
- Will likely revert to mean
- Entry on panic selling

**Rules:**
- Only if fundamentals unchanged
- Only if volume confirms exhaustion
- Small position size (volatility is extreme)
- Quick exit (2-5 days)

---

### **Strategy 4: Trend Following with Vol Confirmation**

**Setup:**
```
Annual Vol:    120%
Quarterly Vol: 130% (increasing)
Monthly Vol:   150% (increasing)
Weekly Vol:    170% (increasing)

Vol Regime: "Accelerating"
Price Trend: Up 50% last month
```

**Action:** 🏃 **RIDE THE TREND**
- Volatility confirming momentum
- Add to winning positions
- Trail stop using weekly vol

**Position Management:**
```python
# Initial entry: 10% of portfolio
# After +20%: Add 5% more
# After +40%: Add 5% more
# Trail stop: 2x weekly volatility
```

---

## 📊 **Volatility Regime Signals**

### **"Accelerating" Regime (Best for Trading)**
```
Weekly > Monthly > Quarterly
```

**Characteristics:**
- Volatility expanding
- Big moves happening NOW
- Best trading environment

**Best Strategies:**
- Momentum trading
- Breakout entries
- Quick scalps

**Example Stocks from Your Universe:**
Look for `vol_regime: "Accelerating"` in scanner output

---

### **"Decelerating" Regime (Caution)**
```
Weekly < Monthly < Quarterly
```

**Characteristics:**
- Volatility contracting
- Cooling down period
- Low probability trades

**Best Strategies:**
- Wait for next setup
- Take profits on existing positions
- Reduce position sizes

---

### **"Mixed" Regime (Transitional)**
```
Weekly high, Monthly low, Quarterly medium
OR various other combinations
```

**Characteristics:**
- Volatility unstable
- Transitioning between regimes
- Uncertain environment

**Best Strategies:**
- Smaller positions
- Faster exits
- More selective entries

---

## 🎯 **Position Sizing with Multi-Timeframe Vol**

### **Conservative Approach (Use Monthly Vol)**

```python
def calculate_position_size(price, monthly_vol, portfolio_value, risk_percent=2):
    """
    Calculate position size based on monthly volatility
    More stable than daily, more responsive than annual
    """
    
    # Risk per trade (2% of portfolio)
    risk_dollars = portfolio_value * (risk_percent / 100)
    
    # Stop loss as function of monthly volatility
    # Use 15% of monthly vol (roughly 1 std dev for 20 days)
    stop_loss_percent = (monthly_vol / 100) * 0.15
    stop_loss_dollars = price * stop_loss_percent
    
    # Position size
    shares = risk_dollars / stop_loss_dollars
    position_value = shares * price
    
    return {
        'shares': int(shares),
        'position_value': position_value,
        'percent_of_portfolio': (position_value / portfolio_value) * 100,
        'stop_loss': price - stop_loss_dollars,
        'risk_dollars': risk_dollars
    }

# Example
result = calculate_position_size(
    price=11.86,
    monthly_vol=150,  # SEMR monthly volatility
    portfolio_value=100000,
    risk_percent=2
)

print(f"Buy {result['shares']} shares")
print(f"Position size: ${result['position_value']:,.2f} ({result['percent_of_portfolio']:.1f}%)")
print(f"Stop loss: ${result['stop_loss']:.2f}")
```

---

## 📈 **Entry Timing with Volatility**

### **Best Entry Points:**

**1. Volatility Expansion Beginning**
```
Quarterly: 100%
Monthly: 100%
Weekly: 120% ← Just crossed above monthly
Daily: 140%

Action: ENTER - Expansion just starting
```

**2. After Volatility Spike Cooldown**
```
Weekly: 200% (was spike)
Now Weekly: 120% (cooled down)
Monthly: 100%

Action: ENTER - Healthy pullback
```

**3. Volume + Volatility Confirmation**
```
Weekly Vol: Rising
Volume: 3x average
Price: Breaking resistance

Action: ENTER - Everything aligned
```

---

## 🛑 **Exit Timing with Volatility**

### **Exit Signals:**

**1. Volatility Peak (Take Profits)**
```
Daily Vol: 300% (extreme)
Weekly Vol: 250%
Monthly Vol: 150%

Signal: Volatility peaked - exit into strength
```

**2. Volatility Compression (Position at Risk)**
```
Was: Weekly 200%, Monthly 180%
Now: Weekly 80%, Monthly 90%

Signal: Momentum fading - exit or reduce
```

**3. Regime Change (Stop Loss)**
```
Was: "Accelerating" regime
Now: "Decelerating" regime

Signal: Trend reversing - exit
```

---

## 💡 **Pro Tips**

### **1. Use Monthly Vol for Most Decisions**
- More stable than daily/weekly
- More responsive than quarterly/annual
- Best for position sizing
- Best for stop placement

### **2. Weekly Vol for Entry Timing**
```
if weekly_vol > monthly_vol:
    # Volatility expanding - good entry time
    signal = "BUY"
else:
    # Wait for expansion
    signal = "WAIT"
```

### **3. Daily Vol for Intraday Trading**
```
if daily_vol > (monthly_vol * 2):
    # Extreme day - fade the move
    strategy = "CONTRARIAN"
else:
    # Normal volatility - follow momentum
    strategy = "TREND_FOLLOW"
```

### **4. Quarterly Vol for Portfolio**
```
if quarterly_vol < 80:
    # Low risk stock
    portfolio_weight = 15-20%
elif quarterly_vol < 150:
    # Medium risk stock
    portfolio_weight = 10-15%
else:
    # High risk stock
    portfolio_weight = 5-10%
```

---

## 📊 **Scanner Output Example**

### **What You'll See:**
```
ticker  price  weekly_vol  monthly_vol  annual_vol  vol_regime
EB      4.43   280%        250%         276%        Accelerating
SEMR    11.86  190%        180%         258%        Accelerating
SOC     6.40   140%        150%         157%        Decelerating
```

### **How to Interpret:**

**EB:**
- Weekly > Monthly → Recent spike
- All high volatility → Consistently aggressive
- Accelerating → Getting more volatile
- **Trade:** Strong buy candidate

**SEMR:**
- Weekly > Monthly → Momentum building
- High across all timeframes → Reliable volatility
- Accelerating → Trend starting
- **Trade:** Good entry point

**SOC:**
- Weekly < Monthly → Cooling down
- Decelerating → Losing momentum
- **Trade:** Wait or exit existing position

---

## 🎓 **Real Trade Example**

### **Trade: SEMR Long Position**

**Analysis:**
```
Date: Dec 12, 2024
Price: $11.86
Daily Vol: 80%
Weekly Vol: 190%
Monthly Vol: 180%
Quarterly Vol: 150%
Annual Vol: 258%
Vol Regime: Accelerating
Volume: 2.2M (normal)
```

**Decision Logic:**
1. ✅ Weekly > Monthly → Volatility expanding
2. ✅ Regime = Accelerating → Momentum building
3. ✅ Volume normal → No exhaustion yet
4. ✅ Monthly vol = 180% → Big moves possible

**Trade Plan:**
```
Entry: $11.86
Position Size: 169 shares ($2,000 investment)
Stop Loss: $10.66 (10% = ~0.6x monthly vol)
Target 1: $14.23 (20% = ~1.1x monthly vol)
Target 2: $16.60 (40% = ~2.2x monthly vol)
Risk: $200 (10% of $2,000)
Reward: $400-$800
Risk/Reward: 1:2 to 1:4
```

**Management:**
- If weekly vol drops below monthly → Exit
- If vol regime → "Decelerating" → Exit
- If volume 3x+ with no price move → Exit
- Trail stop at 1.5x weekly vol

---

## 🚨 **Common Mistakes**

### **1. Using Wrong Timeframe**
❌ Using annual vol for day trading
✅ Use daily/weekly vol for day/swing trading

### **2. Ignoring Regime Changes**
❌ Holding through "Decelerating" regime
✅ Exit when regime changes against you

### **3. Position Sizing on Daily Vol**
❌ Daily vol is too noisy
✅ Use monthly vol for position sizing

### **4. Not Confirming with Volume**
❌ Volatility spike on no volume = fake
✅ Volatility + volume surge = real move

---

## 📚 **Summary**

**Key Takeaways:**
1. Use **monthly volatility** for position sizing
2. Use **weekly volatility** for entry timing
3. Use **volatility regime** for trend direction
4. **"Accelerating"** regime = best trading opportunities
5. Exit when regime changes to **"Decelerating"**

**Your Edge:**
With multi-timeframe volatility, you can:
- Enter trades earlier (detect expansion)
- Size positions better (use monthly vol)
- Exit smarter (detect regime changes)
- Avoid false signals (confirm across timeframes)

This gives you a **massive advantage** over traders using just one volatility metric! 🎯
