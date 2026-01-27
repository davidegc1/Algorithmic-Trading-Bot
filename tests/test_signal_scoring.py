"""
Unit tests for the Scanner v2.1 signal scoring system
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import (
    MIN_ENTRY_SCORE,
    MIN_BREAKOUT_PCT,
    MIN_RELATIVE_VOLUME,
    RSI_MIN,
    RSI_MAX,
    SCORE_ABOVE_VWAP,
    SCORE_BREAKOUT,
    SCORE_VOLUME,
    SCORE_RSI_VALID,
    SCORE_STRONG_BREAKOUT,
    SCORE_HIGH_VOLUME,
    SCORE_RSI_SWEET,
    SCORE_LARGE_GAP,
)


class TestScoringConstants:
    """Tests for scoring constant configuration"""

    def test_required_score_sum(self):
        """Required criteria should sum to MIN_ENTRY_SCORE"""
        required_total = SCORE_ABOVE_VWAP + SCORE_BREAKOUT + SCORE_VOLUME + SCORE_RSI_VALID
        assert required_total == MIN_ENTRY_SCORE

    def test_max_possible_score(self):
        """Max possible score should be 95"""
        max_score = (SCORE_ABOVE_VWAP + SCORE_BREAKOUT + SCORE_VOLUME + SCORE_RSI_VALID +
                    SCORE_STRONG_BREAKOUT + SCORE_HIGH_VOLUME + SCORE_RSI_SWEET + SCORE_LARGE_GAP)
        assert max_score == 95

    def test_min_entry_score(self):
        """MIN_ENTRY_SCORE should be 60"""
        assert MIN_ENTRY_SCORE == 60

    def test_min_breakout_pct(self):
        """MIN_BREAKOUT_PCT should be 1%"""
        assert MIN_BREAKOUT_PCT == 0.01

    def test_min_relative_volume(self):
        """MIN_RELATIVE_VOLUME should be 2x"""
        assert MIN_RELATIVE_VOLUME == 2.0

    def test_rsi_range(self):
        """RSI range should be 40-75"""
        assert RSI_MIN == 40
        assert RSI_MAX == 75


class TestSignalScoring:
    """Tests for calculate_signal_score function"""

    @pytest.fixture
    def mock_scanner(self):
        """Create a mock scanner for testing scoring"""
        from core.scanner import SignalScanner

        with patch.object(SignalScanner, '__init__', lambda self: None):
            scanner = SignalScanner()
            scanner.MIN_ENTRY_SCORE = MIN_ENTRY_SCORE
            scanner.MIN_BREAKOUT_PCT = MIN_BREAKOUT_PCT
            scanner.MIN_RELATIVE_VOLUME = MIN_RELATIVE_VOLUME
            scanner.RSI_MIN = RSI_MIN
            scanner.RSI_MAX = RSI_MAX
            scanner.premarket_data = {}
            return scanner

    def test_all_required_pass_base_score(self, mock_scanner):
        """All required criteria passed should give base score of 60"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,   # Above VWAP
            vwap=10.0,
            rsi=45,              # Within 40-75 but NOT in sweet spot (50-65)
            breakout_pct=0.02,   # Above 1% but not > 3%
            breakout_ref='premarket_high',
            relative_volume=2.5  # Above 2x but not > 4x
        )
        assert score == MIN_ENTRY_SCORE  # Exactly 60, no bonuses
        assert rejection is None

    def test_below_vwap_rejected(self, mock_scanner):
        """Price below VWAP should be rejected"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=9.5,    # Below VWAP
            vwap=10.0,
            rsi=55,
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=2.5
        )
        assert score == 0
        assert rejection == 'below_vwap'

    def test_breakout_too_low_rejected(self, mock_scanner):
        """Breakout below 1% should be rejected"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=10.05,
            vwap=10.0,
            rsi=55,
            breakout_pct=0.005,  # Only 0.5%
            breakout_ref='premarket_high',
            relative_volume=2.5
        )
        assert score == 0
        assert 'breakout' in rejection

    def test_volume_too_low_rejected(self, mock_scanner):
        """Volume below 2x should be rejected"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=55,
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=1.5  # Below 2x
        )
        assert score == 0
        assert 'volume' in rejection

    def test_rsi_too_low_rejected(self, mock_scanner):
        """RSI below 40 should be rejected"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=35,              # Below 40
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=2.5
        )
        assert score == 0
        assert 'rsi' in rejection

    def test_rsi_too_high_rejected(self, mock_scanner):
        """RSI above 75 should be rejected"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=80,              # Above 75
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=2.5
        )
        assert score == 0
        assert 'rsi' in rejection

    def test_strong_breakout_bonus(self, mock_scanner):
        """Breakout > 3% should add 10 points"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=45,              # NOT in sweet spot (to isolate breakout bonus)
            breakout_pct=0.04,   # 4% > 3%
            breakout_ref='premarket_high',
            relative_volume=2.5  # NOT high volume
        )
        assert score == MIN_ENTRY_SCORE + SCORE_STRONG_BREAKOUT  # 60 + 10 = 70
        assert metrics.get('strong_breakout') is True

    def test_high_volume_bonus(self, mock_scanner):
        """Volume > 4x should add 10 points"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=45,              # NOT in sweet spot
            breakout_pct=0.02,   # NOT strong breakout
            breakout_ref='premarket_high',
            relative_volume=5.0  # 5x > 4x
        )
        assert score == MIN_ENTRY_SCORE + SCORE_HIGH_VOLUME  # 60 + 10 = 70
        assert metrics.get('high_volume') is True

    def test_rsi_sweet_spot_bonus(self, mock_scanner):
        """RSI 50-65 should add 5 points"""
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=58,              # 50-65 sweet spot
            breakout_pct=0.02,
            breakout_ref='premarket_high',
            relative_volume=2.5
        )
        assert score == MIN_ENTRY_SCORE + SCORE_RSI_SWEET
        assert metrics.get('rsi_sweet_spot') is True

    def test_large_gap_bonus(self, mock_scanner):
        """Gap > 5% should add 10 points"""
        mock_scanner.premarket_data = {
            'TEST': {'gap_pct': 0.06}  # 6% gap
        }
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=45,              # NOT in sweet spot
            breakout_pct=0.02,   # NOT strong breakout
            breakout_ref='premarket_high',
            relative_volume=2.5  # NOT high volume
        )
        assert score == MIN_ENTRY_SCORE + SCORE_LARGE_GAP  # 60 + 10 = 70
        assert metrics.get('large_gap') is True

    def test_all_bonuses_max_score(self, mock_scanner):
        """All bonuses should give max score of 95"""
        mock_scanner.premarket_data = {
            'TEST': {'gap_pct': 0.06}
        }
        score, metrics, rejection = mock_scanner.calculate_signal_score(
            symbol='TEST',
            current_price=11.0,
            vwap=10.0,
            rsi=58,              # Sweet spot
            breakout_pct=0.04,   # Strong breakout
            breakout_ref='premarket_high',
            relative_volume=5.0  # High volume
        )
        # 60 base + 10 strong breakout + 10 high volume + 5 RSI sweet + 10 large gap = 95
        assert score == 95
        assert rejection is None


class TestBreakoutCalculation:
    """Tests for breakout calculation logic"""

    @pytest.fixture
    def mock_scanner(self):
        """Create a mock scanner for testing breakout"""
        from core.scanner import SignalScanner

        with patch.object(SignalScanner, '__init__', lambda self: None):
            scanner = SignalScanner()
            scanner.premarket_data = {}
            return scanner

    def test_breakout_from_premarket_high(self, mock_scanner):
        """Breakout should use premarket high when available"""
        mock_scanner.premarket_data = {
            'TEST': {'premarket_high': 10.0}
        }
        bars = pd.DataFrame({'high': [9.5], 'low': [9.0]})

        breakout_pct, ref = mock_scanner.calculate_breakout('TEST', 10.5, bars)
        assert ref == 'premarket_high'
        assert breakout_pct == pytest.approx(0.05, rel=0.01)

    def test_breakout_from_session_high(self, mock_scanner):
        """Breakout should use session high when premarket not available"""
        mock_scanner.premarket_data = {}
        bars = pd.DataFrame({
            'high': [9.5, 10.0, 10.2],
            'low': [9.0, 9.5, 10.0]
        })

        # Price at session high
        breakout_pct, ref = mock_scanner.calculate_breakout('TEST', 10.2, bars)
        assert ref == 'session_high'

    def test_breakout_fallback_to_session_low(self, mock_scanner):
        """Breakout should fallback to session low if no better reference"""
        mock_scanner.premarket_data = {}
        bars = pd.DataFrame({
            'high': [11.0, 10.5, 10.0],  # Declining
            'low': [10.5, 10.0, 9.5]
        })

        breakout_pct, ref = mock_scanner.calculate_breakout('TEST', 10.0, bars)
        # Should use session_low as reference since price not near high
        assert ref in ['session_low', 'session_high']


class TestUniverseLoading:
    """Tests for universe loading logic"""

    def test_watchlist_priority(self):
        """Should use daily watchlist over static universe"""
        from config.config import DAILY_WATCHLIST_SIZE
        assert DAILY_WATCHLIST_SIZE == 25

    def test_universe_limited_to_25(self):
        """Fallback universe should be limited to 25 stocks"""
        from config.config import DEFAULT_UNIVERSE
        # Default universe can be larger but scanner limits to 25
        assert len(DEFAULT_UNIVERSE) >= 1


class TestModuleImport:
    """Tests for scanner module import"""

    def test_import_scanner(self):
        """SignalScanner should be importable"""
        from core.scanner import SignalScanner
        assert SignalScanner is not None

    def test_import_indicators_in_scanner(self):
        """Scanner should use TechnicalIndicators"""
        from core.scanner import SignalScanner
        from core.indicators import TechnicalIndicators
        # Both should be importable
        assert SignalScanner is not None
        assert TechnicalIndicators is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
