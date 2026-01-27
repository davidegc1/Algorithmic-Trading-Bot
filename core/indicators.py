"""
TECHNICAL INDICATORS MODULE
Provides VWAP, RSI, and other indicators for signal generation

All indicators are calculated from OHLCV bar data.
"""

import pandas as pd
import numpy as np
from typing import Optional


class TechnicalIndicators:
    """Calculate technical indicators from price/volume data"""

    @staticmethod
    def calculate_vwap(bars: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price

        VWAP = Cumulative(Typical Price x Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3

        Args:
            bars: DataFrame with 'high', 'low', 'close', 'volume' columns

        Returns:
            Series of VWAP values
        """
        if bars.empty:
            return pd.Series(dtype=float)

        typical_price = (bars['high'] + bars['low'] + bars['close']) / 3
        cumulative_tp_vol = (typical_price * bars['volume']).cumsum()
        cumulative_vol = bars['volume'].cumsum()

        # Avoid division by zero
        cumulative_vol = cumulative_vol.replace(0, np.nan)
        vwap = cumulative_tp_vol / cumulative_vol

        return vwap

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

        Args:
            prices: Series of closing prices
            period: RSI period (default 14)

        Returns:
            Series of RSI values (0-100)
        """
        if len(prices) < period + 1:
            return pd.Series([50] * len(prices), index=prices.index)

        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Use exponential moving average for smoother RSI
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        # Avoid division by zero
        avg_loss = avg_loss.replace(0, 0.0001)

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_relative_volume(
        current_volume: int,
        bars: pd.DataFrame,
        lookback: int = 20
    ) -> float:
        """
        Calculate relative volume vs historical average

        Args:
            current_volume: Current bar's volume
            bars: Historical bars with 'volume' column
            lookback: Number of bars for average calculation

        Returns:
            Relative volume ratio (e.g., 2.5 = 2.5x average)
        """
        if bars.empty or len(bars) < 2:
            return 1.0

        lookback = min(lookback, len(bars) - 1)
        avg_volume = bars['volume'].tail(lookback).mean()

        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    @staticmethod
    def calculate_atr(bars: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range

        True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))

        Args:
            bars: DataFrame with 'high', 'low', 'close' columns
            period: ATR period

        Returns:
            Current ATR value
        """
        if len(bars) < period + 1:
            return 0.0

        high = bars['high']
        low = bars['low']
        close = bars['close']
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0

    @staticmethod
    def is_above_vwap(current_price: float, vwap: float) -> bool:
        """Check if price is above VWAP"""
        return current_price > vwap

    @staticmethod
    def is_rsi_valid(
        rsi: float,
        min_rsi: float = 40,
        max_rsi: float = 75
    ) -> bool:
        """
        Check if RSI is in valid range for momentum entry

        - RSI < 40: Potentially weak momentum
        - RSI 40-75: Good momentum, not overbought
        - RSI > 75: Overbought, risky entry
        """
        if pd.isna(rsi):
            return False
        return min_rsi <= rsi <= max_rsi

    @staticmethod
    def is_rsi_sweet_spot(rsi: float) -> bool:
        """Check if RSI is in the sweet spot (50-65)"""
        if pd.isna(rsi):
            return False
        return 50 <= rsi <= 65

    @staticmethod
    def calculate_breakout_percent(
        current_price: float,
        reference_price: float
    ) -> float:
        """
        Calculate breakout percentage from reference level

        Args:
            current_price: Current price
            reference_price: Pre-market high, prior day high, etc.

        Returns:
            Breakout percentage (e.g., 0.03 = 3% above reference)
        """
        if reference_price <= 0:
            return 0.0
        return (current_price - reference_price) / reference_price

    @staticmethod
    def calculate_velocity(
        bars: pd.DataFrame,
        periods: int = 5
    ) -> float:
        """
        Calculate price velocity (rate of change)

        Args:
            bars: DataFrame with 'close' column
            periods: Number of periods for velocity calculation

        Returns:
            Velocity as percentage per period
        """
        if len(bars) < periods + 1:
            return 0.0

        start_price = bars['close'].iloc[-(periods + 1)]
        end_price = bars['close'].iloc[-1]

        if start_price <= 0:
            return 0.0

        total_change = (end_price - start_price) / start_price
        velocity = total_change / periods

        return velocity

    @staticmethod
    def calculate_acceleration(
        bars: pd.DataFrame,
        velocity_period: int = 5
    ) -> float:
        """
        Calculate price acceleration (change in velocity)

        Args:
            bars: DataFrame with 'close' column
            velocity_period: Period for velocity calculation

        Returns:
            Acceleration value (positive = speeding up, negative = slowing down)
        """
        if len(bars) < (velocity_period * 2) + 1:
            return 0.0

        # Calculate current velocity (last N periods)
        current_velocity = TechnicalIndicators.calculate_velocity(bars, velocity_period)

        # Calculate prior velocity (N periods before that)
        prior_bars = bars.iloc[:-(velocity_period)]
        prior_velocity = TechnicalIndicators.calculate_velocity(prior_bars, velocity_period)

        if prior_velocity == 0:
            return 1.0 if current_velocity > 0 else 0.0

        # Acceleration = current_velocity / prior_velocity
        # > 1 means accelerating, < 1 means decelerating
        return current_velocity / prior_velocity if prior_velocity != 0 else 1.0
