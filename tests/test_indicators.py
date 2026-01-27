"""
Unit tests for the TechnicalIndicators module
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.indicators import TechnicalIndicators


class TestVWAP:
    """Tests for VWAP calculation"""

    def test_vwap_basic(self):
        """VWAP should weight price by volume"""
        bars = pd.DataFrame({
            'high': [10.0, 11.0, 12.0],
            'low': [9.0, 10.0, 11.0],
            'close': [9.5, 10.5, 11.5],
            'volume': [1000, 2000, 1000]
        })
        vwap = TechnicalIndicators.calculate_vwap(bars)
        # Higher volume bar should pull VWAP toward its price
        assert len(vwap) == 3
        assert vwap.iloc[-1] > 0

    def test_vwap_empty(self):
        """VWAP of empty dataframe should be empty"""
        bars = pd.DataFrame()
        vwap = TechnicalIndicators.calculate_vwap(bars)
        assert len(vwap) == 0

    def test_vwap_single_bar(self):
        """VWAP of single bar should be typical price"""
        bars = pd.DataFrame({
            'high': [10.0],
            'low': [8.0],
            'close': [9.0],
            'volume': [1000]
        })
        vwap = TechnicalIndicators.calculate_vwap(bars)
        expected_typical = (10.0 + 8.0 + 9.0) / 3  # = 9.0
        assert abs(vwap.iloc[0] - expected_typical) < 0.01

    def test_vwap_weighted_correctly(self):
        """VWAP should be weighted toward high-volume bars"""
        # Bar 1: price ~10, volume 100
        # Bar 2: price ~20, volume 900
        # VWAP should be closer to 20 than 10
        bars = pd.DataFrame({
            'high': [11.0, 21.0],
            'low': [9.0, 19.0],
            'close': [10.0, 20.0],
            'volume': [100, 900]
        })
        vwap = TechnicalIndicators.calculate_vwap(bars)
        # Expected: closer to 20 due to higher volume
        assert vwap.iloc[-1] > 15  # Should be weighted toward 20


class TestRSI:
    """Tests for RSI calculation"""

    def test_rsi_range(self):
        """RSI should be between 0 and 100"""
        prices = pd.Series([10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15, 14, 13, 12])
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert all(0 <= r <= 100 for r in rsi.dropna())

    def test_rsi_uptrend(self):
        """RSI should be high in strong uptrend"""
        prices = pd.Series(range(1, 25))  # Continuous uptrend
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert rsi.iloc[-1] > 70

    def test_rsi_downtrend(self):
        """RSI should be low in strong downtrend"""
        prices = pd.Series(range(25, 1, -1))  # Continuous downtrend
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert rsi.iloc[-1] < 30

    def test_rsi_short_series(self):
        """RSI with short series should return default values"""
        prices = pd.Series([10, 11, 12])
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        # Should return default value (50) for series shorter than period
        assert all(r == 50 for r in rsi)

    def test_rsi_neutral(self):
        """RSI with mixed movement should be around 50"""
        # Alternating up/down should give RSI around 50
        prices = pd.Series([10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11])
        rsi = TechnicalIndicators.calculate_rsi(prices)
        assert 40 <= rsi.iloc[-1] <= 60


class TestRelativeVolume:
    """Tests for relative volume calculation"""

    def test_relative_volume_2x(self):
        """2x volume should return ~2.0"""
        bars = pd.DataFrame({'volume': [1000] * 20})
        rel_vol = TechnicalIndicators.calculate_relative_volume(2000, bars)
        assert abs(rel_vol - 2.0) < 0.1

    def test_relative_volume_normal(self):
        """Average volume should return ~1.0"""
        bars = pd.DataFrame({'volume': [1000] * 20})
        rel_vol = TechnicalIndicators.calculate_relative_volume(1000, bars)
        assert abs(rel_vol - 1.0) < 0.1

    def test_relative_volume_empty(self):
        """Empty bars should return 1.0"""
        bars = pd.DataFrame()
        rel_vol = TechnicalIndicators.calculate_relative_volume(1000, bars)
        assert rel_vol == 1.0

    def test_relative_volume_half(self):
        """Half volume should return ~0.5"""
        bars = pd.DataFrame({'volume': [1000] * 20})
        rel_vol = TechnicalIndicators.calculate_relative_volume(500, bars)
        assert abs(rel_vol - 0.5) < 0.1


class TestATR:
    """Tests for ATR calculation"""

    def test_atr_basic(self):
        """ATR should be positive for volatile data"""
        np.random.seed(42)
        bars = pd.DataFrame({
            'high': [10 + i + np.random.rand() for i in range(20)],
            'low': [10 + i - np.random.rand() for i in range(20)],
            'close': [10 + i for i in range(20)]
        })
        atr = TechnicalIndicators.calculate_atr(bars)
        assert atr > 0

    def test_atr_short_series(self):
        """ATR with short series should return 0"""
        bars = pd.DataFrame({
            'high': [10, 11, 12],
            'low': [9, 10, 11],
            'close': [9.5, 10.5, 11.5]
        })
        atr = TechnicalIndicators.calculate_atr(bars, period=14)
        assert atr == 0.0


class TestBreakout:
    """Tests for breakout calculation"""

    def test_breakout_positive(self):
        """Price above reference should give positive breakout"""
        pct = TechnicalIndicators.calculate_breakout_percent(10.5, 10.0)
        assert pct == pytest.approx(0.05, rel=0.01)

    def test_breakout_negative(self):
        """Price below reference should give negative breakout"""
        pct = TechnicalIndicators.calculate_breakout_percent(9.5, 10.0)
        assert pct == pytest.approx(-0.05, rel=0.01)

    def test_breakout_zero_reference(self):
        """Zero reference price should return 0"""
        pct = TechnicalIndicators.calculate_breakout_percent(10.0, 0)
        assert pct == 0.0

    def test_breakout_exact(self):
        """Price at reference should give 0% breakout"""
        pct = TechnicalIndicators.calculate_breakout_percent(10.0, 10.0)
        assert pct == 0.0


class TestRSIValidation:
    """Tests for RSI validation functions"""

    def test_rsi_valid_range(self):
        """RSI 50 should be valid"""
        assert TechnicalIndicators.is_rsi_valid(50, 40, 75) is True

    def test_rsi_at_min(self):
        """RSI at min boundary should be valid"""
        assert TechnicalIndicators.is_rsi_valid(40, 40, 75) is True

    def test_rsi_at_max(self):
        """RSI at max boundary should be valid"""
        assert TechnicalIndicators.is_rsi_valid(75, 40, 75) is True

    def test_rsi_too_low(self):
        """RSI 30 should be invalid (< 40)"""
        assert TechnicalIndicators.is_rsi_valid(30, 40, 75) is False

    def test_rsi_too_high(self):
        """RSI 80 should be invalid (> 75)"""
        assert TechnicalIndicators.is_rsi_valid(80, 40, 75) is False

    def test_rsi_nan(self):
        """NaN RSI should be invalid"""
        assert TechnicalIndicators.is_rsi_valid(float('nan'), 40, 75) is False

    def test_rsi_sweet_spot_in(self):
        """RSI 55 should be in sweet spot"""
        assert TechnicalIndicators.is_rsi_sweet_spot(55) is True

    def test_rsi_sweet_spot_out(self):
        """RSI 45 should not be in sweet spot"""
        assert TechnicalIndicators.is_rsi_sweet_spot(45) is False

    def test_rsi_sweet_spot_boundaries(self):
        """RSI at boundaries (50, 65) should be in sweet spot"""
        assert TechnicalIndicators.is_rsi_sweet_spot(50) is True
        assert TechnicalIndicators.is_rsi_sweet_spot(65) is True


class TestVelocity:
    """Tests for velocity calculation"""

    def test_velocity_positive(self):
        """Upward movement should give positive velocity"""
        bars = pd.DataFrame({
            'close': [10.0, 10.2, 10.4, 10.6, 10.8, 11.0]
        })
        velocity = TechnicalIndicators.calculate_velocity(bars, periods=5)
        assert velocity > 0

    def test_velocity_negative(self):
        """Downward movement should give negative velocity"""
        bars = pd.DataFrame({
            'close': [11.0, 10.8, 10.6, 10.4, 10.2, 10.0]
        })
        velocity = TechnicalIndicators.calculate_velocity(bars, periods=5)
        assert velocity < 0

    def test_velocity_short_series(self):
        """Short series should return 0"""
        bars = pd.DataFrame({'close': [10.0, 10.5]})
        velocity = TechnicalIndicators.calculate_velocity(bars, periods=5)
        assert velocity == 0.0


class TestAcceleration:
    """Tests for acceleration calculation"""

    def test_acceleration_speeding_up(self):
        """Accelerating price should give > 1"""
        # Slow then fast movement
        bars = pd.DataFrame({
            'close': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5,  # slow
                      10.7, 11.0, 11.4, 11.9, 12.5]         # fast
        })
        accel = TechnicalIndicators.calculate_acceleration(bars, velocity_period=5)
        assert accel > 1.0

    def test_acceleration_slowing_down(self):
        """Decelerating price should give < 1"""
        # Fast then slow movement
        bars = pd.DataFrame({
            'close': [10.0, 10.5, 11.0, 11.5, 12.0, 12.5,  # fast
                      12.6, 12.7, 12.8, 12.9, 13.0]         # slow
        })
        accel = TechnicalIndicators.calculate_acceleration(bars, velocity_period=5)
        assert accel < 1.0


class TestAboveVWAP:
    """Tests for VWAP comparison"""

    def test_above_vwap(self):
        """Price above VWAP should return True"""
        assert TechnicalIndicators.is_above_vwap(10.5, 10.0) is True

    def test_below_vwap(self):
        """Price below VWAP should return False"""
        assert TechnicalIndicators.is_above_vwap(9.5, 10.0) is False

    def test_at_vwap(self):
        """Price at VWAP should return False (not strictly above)"""
        assert TechnicalIndicators.is_above_vwap(10.0, 10.0) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
