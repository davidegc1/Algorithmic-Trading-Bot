# Trading Bot Directory Structure

## New Organization (Reorganized)

```
trading/
├── core/                    # Core trading services
│   ├── __init__.py
│   ├── scanner.py           # Scanner service (generates buy signals)
│   ├── buyer.py             # Buyer service (executes buy orders)
│   ├── monitor.py           # Monitor service (tracks positions)
│   ├── seller.py            # Seller service (executes sell orders)
│   ├── orchestrator.py      # Orchestrator (manages all services)
│   └── shared_state.py      # Shared state management utilities
│
├── scripts/                 # Utility scripts
│   ├── __init__.py
│   ├── universe_builder.py  # Universe builder utility
│   ├── universe_manager.py # Universe management
│   ├── universe_integration.py
│   ├── alpaca_integration.py
│   ├── volatile_scanner_advanced.py
│   ├── volatile_stock_scanner.py
│   ├── watchlist_monitor.py
│   ├── run_scanner.py
│   └── test_nasdaq_fix.py
│
├── config/                  # Configuration files
│   ├── __init__.py
│   ├── config.py            # Main configuration
│   └── README.md
│
├── state/                   # State files (JSON, PID files)
│   ├── .gitkeep
│   ├── signals.json         # Buy signals from scanner
│   ├── positions.json       # Active positions
│   ├── sell_signals.json    # Sell signals from monitor
│   ├── trades.json          # Completed trade history
│   ├── cooldowns.json       # Cooldown tracking
│   ├── orchestrator_status.json
│   └── orchestrator.pid
│
├── logs/                    # Log files
│   ├── .gitkeep
│   ├── scanner.log
│   ├── buyer.log
│   ├── monitor.log
│   ├── seller.log
│   └── orchestrator.log
│
├── legacy/                  # Legacy/alternative implementation
│   └── trading_bot/         # Original single-bot implementation
│       ├── trading_bot.py
│       ├── start.py
│       ├── analyze_trades.py
│       ├── view_logs.py
│       ├── utils.py
│       ├── config.py
│       └── README.md
│
├── universes/               # Generated universe files
│   └── universe_YYYYMMDD_HHMMSS/
│       ├── universe.py
│       ├── universe_data.csv
│       ├── universe_tickers.txt
│       ├── metadata.json
│       └── README.md
│
├── data/                    # Data files
│   └── custom_universe.py
│
├── docs/                    # Documentation
│   ├── README.md
│   ├── README_SCANNERS.md
│   ├── UNIVERSE_BUILDER_GUIDE.md
│   ├── VOLATILITY_GUIDE.md
│   ├── MULTITIMEFRAME_TRADING_GUIDE.md
│   └── CHANGELOG_CLEANED_TICKERS.md
│
├── tests/                   # Tests
│   └── __init__.py
│
├── .gitignore
├── requirements.txt
├── README.md
├── ACTION_PLAN.md
├── AUDIT_REPORT.md
├── STRUCTURE.md             # This file
├── custom_universe.py        # Active universe (generated)
└── universe_builder.py      # ⚠️ DUPLICATE - Consider removing (see scripts/universe_builder.py)
```

## Key Changes

### 1. Core Services Moved to `core/`
- All main trading services are now in `core/` directory
- Services can be run as modules: `python -m core.scanner`
- Imports updated to use `from core.shared_state import ...`

### 2. State Files in `state/`
- All JSON state files moved to `state/` directory
- PID files also in `state/`
- Automatically created on first use

### 3. Log Files in `logs/`
- All log files moved to `logs/` directory
- Organized and easy to find

### 4. Configuration in `config/`
- Configuration files moved to `config/` directory
- Clear separation of concerns

### 5. Legacy Code in `legacy/`
- Original `trading_bot/` implementation moved to `legacy/`
- Kept for reference but not actively used

## Running Services

### Using Orchestrator (Recommended)
```bash
# Start all services
python -m core.orchestrator start

# Stop all services
python -m core.orchestrator stop

# Check status
python -m core.orchestrator status

# Restart all
python -m core.orchestrator restart

# Monitor and auto-restart
python -m core.orchestrator monitor
```

### Running Individual Services
```bash
# Scanner
python -m core.scanner

# Buyer
python -m core.buyer

# Monitor
python -m core.monitor

# Seller
python -m core.seller
```

## File Path Updates

All file paths have been updated to use the new structure:
- State files: `state/cooldowns.json`, `state/positions.json`, etc.
- Log files: `logs/scanner.log`, `logs/buyer.log`, etc.
- Imports: `from core.shared_state import ...`

## Notes

- **Duplicate File**: `universe_builder.py` exists in both root and `scripts/`. The root version appears to be a duplicate. Consider removing it.
- **Custom Universe**: `custom_universe.py` in root is a generated file and should remain there.
- **State & Logs**: Directories are created automatically on first use.

## Migration Complete

All imports and file paths have been updated. The system is ready to use with the new structure.
