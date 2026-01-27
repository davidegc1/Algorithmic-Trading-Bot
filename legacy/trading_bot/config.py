"""
STRATEGY CONFIGURATION
All tunable parameters in one place
"""

# ============================================================================
# POSITION SIZING
# ============================================================================
MAX_POSITIONS = 20                  # Maximum concurrent positions
POSITION_SIZE_STANDARD = 0.05       # 5% of capital per position
POSITION_SIZE_STRONG = 0.07         # 7% for strong signals (score 90+)

# ============================================================================
# RISK MANAGEMENT
# ============================================================================
STOP_LOSS_PCT = 0.025              # 2.5% hard stop
BREAKEVEN_PROFIT = 0.10            # Move stop to breakeven at +10%

# Trailing stops (profit_level: trailing_pct)
TRAILING_STOPS = {
    0.10: 0.05,   # +10-20%: 5% trailing stop
    0.20: 0.10,   # +20-40%: 10% trailing stop
    0.40: 0.15,   # +40-70%: 15% trailing stop
    0.70: 0.20    # +70%+: 20% trailing stop
}

# ============================================================================
# ENTRY REQUIREMENTS
# ============================================================================
BREAKOUT_5MIN_PCT = 0.04           # 4% breakout on 5-min chart (REQUIRED)
BREAKOUT_2MIN_PCT = 0.03           # 3% breakout on 2-min chart (BONUS)
VOLUME_RATIO_MIN = 2.0             # 2x average volume (REQUIRED)
ACCELERATION_MIN = 1.2             # Acceleration threshold (BONUS)
MIN_ENTRY_SCORE = 70               # Minimum score to enter trade

# ============================================================================
# VOLATILITY FILTERS
# ============================================================================
MIN_ATR_PCT = 0.05                 # 5% daily ATR minimum
HIGH_VOLATILITY_ATR = 0.10         # 10% for using 3-min candles

# ============================================================================
# DECELERATION EXIT
# ============================================================================
DECEL_EXIT_THRESHOLD = 0.5         # Exit if A < 0.5 while in profit
DECEL_TIGHTEN_THRESHOLD = 0.8      # Tighten stop if A < 0.8
MIN_PROFIT_FOR_DECEL_CHECK = 0.05  # Only check decel if >5% profit

# ============================================================================
# COOLDOWN
# ============================================================================
COOLDOWN_MINUTES = 15              # Minutes before re-entering same symbol

# ============================================================================
# SCANNING
# ============================================================================
SCAN_INTERVAL_SECONDS = 60         # Scan universe every 60 seconds
TIMEFRAME_PRIMARY = '5Min'         # Primary timeframe for signals
TIMEFRAME_FAST = '2Min'            # Fast timeframe for V1
TIMEFRAME_CONTEXT = '15Min'        # Context timeframe for trend

# ============================================================================
# SCORING SYSTEM
# ============================================================================
SCORE_5MIN_BREAKOUT = 25           # Points for 5-min breakout (REQUIRED)
SCORE_VOLUME = 20                  # Points for volume confirmation (REQUIRED)
SCORE_15MIN_GREEN = 10             # Points for 15-min green (REQUIRED)
SCORE_2MIN_BREAKOUT = 15           # Bonus points for 2-min breakout
SCORE_VELOCITY_RATIO = 15          # Bonus points for V1 > V2
SCORE_ACCELERATION = 15            # Bonus points for A > 1.2
SCORE_ACCELERATION_MED = 10        # Points for A > 1.0 but < 1.2

# ============================================================================
# DEFAULT WATCHLIST (if no universe file provided)
# ============================================================================
DEFAULT_UNIVERSE = [
    "CAPR", "AHMA", "PLRZ", "CETX", "KTTA", "NCPL", "ZYXI", "MNDR", "KITT", "CETY",
    "EPSM", "CMCT", "BEAT", "WHLR", "SGBX", "AEHL", "IRBT", "RZLT", "CYPH", "LFS",
    "MIGI", "EB", "QTTB", "RUBI", "SEMR", "PETS", "CYCU", "IBIO", "PMCB", "SLMT",
    "AMIX", "QCLS", "AMBR", "KALA", "CGTL", "RPGL", "ZSPC", "JFBR", "LOBO", "BENF",
    "VEEE", "SIDU", "JANX", "ONMD", "DVLT", "SSP", "CGC", "FTEL", "FULC", "TLRY",
    "AGIO", "IVDA", "NXXT", "SGML", "INV", "BCAB", "PMAX", "AVXL", "AIIO", "YDKG",
    "LNAI", "ABVE", "OSRH", "SNTI", "TSSI", "FRGT", "QH", "BYND", "BTTC", "VOR",
    "IVVD", "GTBP", "PBM", "DGXX", "EPWK", "UP", "MNTS", "VCIG", "CGEM", "ANVS",
    "TNYA", "ABTC", "SOC", "GEMI", "IOBT", "NFE", "DEFT", "MGRX", "HOVR", "NUKK",
    "NNOX", "BTQ", "SLNH", "RITR", "GWH", "GLTO", "SELX", "CSIQ", "AUID", "ONFO",
    "HUBC", "TE", "BFLY", "SLE", "UFG", "NKLR", "IBG", "MBAI", "FLWS", "DFLI",
    "AEVA", "SUIG", "ETHZ", "NUAI", "TOI", "MTC", "PRLD", "DCX", "POET", "MAGN",
    "SANA", "TBH", "WGRX", "OMER", "LITM", "AIHS", "NXDR", "SLRX", "TROX", "HSDT",
    "CRML", "XHLD", "AREC", "NVA", "YYAI", "MSGM", "HCTI", "RR", "CRNC", "PGEN",
    "AREB", "TEAD", "BLNE", "PALI", "LAZR", "PRHI", "AIRS", "LENZ", "EVTL", "ATON",
    "ORBS", "SPRC", "BMEA", "COOT", "CODI", "STIM", "AKAN", "FGNX", "ZYME", "LMFA",
    "MBOT", "DFDV", "ANNX", "ASPI", "CAPT", "GLMD", "BNAI", "UPXI", "AXTI", "XXII",
    "CAN", "PACB", "ARTV", "BNC", "BTCS", "LUNG", "BOXL", "HLF", "ZNB", "MOBX",
    "NB", "IRWD", "FEMY", "AERT", "BKKT", "ENLV", "ERNA", "AGL", "ABAT", "HBIO",
    "IMSR", "CMBM", "ADCT", "PSNL", "EVAX", "SPRY", "RBNE", "RVPH", "MIST", "ECX"
]

# ============================================================================
# ADAPTIVE TIMEFRAMES (based on ATR)
# ============================================================================
USE_ADAPTIVE_TIMEFRAMES = False     # Set True to use different timeframes based on volatility

ADAPTIVE_TIMEFRAMES = {
    'extreme': {  # ATR > 10%
        'primary': '2Min',
        'confirmation': '5Min',
        'context': '15Min'
    },
    'high': {  # ATR 7-10%
        'primary': '3Min',
        'confirmation': '10Min',
        'context': '20Min'
    },
    'medium': {  # ATR 5-7%
        'primary': '5Min',
        'confirmation': '15Min',
        'context': '30Min'
    },
    'low': {  # ATR < 5%
        'primary': '10Min',
        'confirmation': '30Min',
        'context': '60Min'
    }
}

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = 'INFO'                 # DEBUG, INFO, WARNING, ERROR
LOG_FILE = 'trading_bot.log'
LOG_TO_CONSOLE = True

# ============================================================================
# ALPACA API
# ============================================================================
PAPER_TRADING = True               # Use paper trading by default
API_VERSION = 'v2'

# ============================================================================
# BACKTESTING
# ============================================================================
BACKTEST_START_DATE = '2024-01-01'
BACKTEST_END_DATE = '2024-12-31'
BACKTEST_INITIAL_CAPITAL = 10000
