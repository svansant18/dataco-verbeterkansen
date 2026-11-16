import math
import sys

import pandas as pd
import pytest

from analysis.kpis import discount_margin_correlation, safe_percent, safe_ratio


def _lines(rate, profit):
    """Omzet 1 per lijn, zodat marge = winst."""
    return pd.DataFrame({"Order Item Discount Rate": rate, "Order Profit Per Order": profit, "Order Item Total": [1.0] * len(rate)})


def test_spearman_with_ties_matches_hand_calculation(monkeypatch):
    # Zonder scipy: pandas' corr(method="spearman") zou hier een ImportError geven.
    monkeypatch.setitem(sys.modules, "scipy", None)
    monkeypatch.setitem(sys.modules, "scipy.stats", None)
    result = discount_margin_correlation(_lines([0.0, 0.0, 0.10, 0.20], [0.3, 0.1, 0.2, 0.4]))
    # Gemiddelde rangen korting [1.5, 1.5, 3, 4], marge [3, 1, 2, 4] -> r = 3 / sqrt(4.5 * 5)
    assert result["spearman"] == pytest.approx(3 / math.sqrt(22.5))
    assert result["n"] == 4


def test_spearman_is_one_for_monotone_nonlinear_relation():
    result = discount_margin_correlation(_lines([0.0, 0.05, 0.10, 0.20], [0.01, 0.02, 0.10, 0.90]))
    assert result["spearman"] == pytest.approx(1.0)
    assert result["pearson"] < 1.0


def test_weighted_margin_from_totals():
    assert safe_percent(30, 200) == 15


def test_zero_denominator_is_missing_not_zero():
    assert safe_percent(10, 0) is None


def test_nonfinite_is_missing():
    assert safe_ratio(math.inf, 100) is None


def test_invalid_input_is_missing():
    assert safe_ratio("unknown", 100) is None
