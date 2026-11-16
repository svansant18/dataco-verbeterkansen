import pandas as pd
import pytest

from pipeline import audit_order_grain
from analysis.kpis import count_unique_boolean_events, safe_percent


def test_one_order_with_three_lines_counts_only_once():
    df = pd.DataFrame({"id": [1001, 1001, 1001, 1002], "late": [True, True, True, False]})
    numerator, denominator = count_unique_boolean_events(df, id_col="id", event_col="late")
    assert (numerator, denominator) == (1, 2)
    assert safe_percent(numerator, denominator) == 50.0


def test_conflicting_status_is_not_silently_accepted():
    df = pd.DataFrame({"id": [1001, 1001], "late": [True, False]})
    with pytest.raises(ValueError, match="Conflicting"):
        count_unique_boolean_events(df, id_col="id", event_col="late")


def test_missing_status_is_not_silently_accepted():
    with pytest.raises(ValueError):
        count_unique_boolean_events(pd.DataFrame({"id": [1], "late": [None]}), id_col="id", event_col="late")


def test_multi_category_order_grain_audit_does_not_expose_raw_ids():
    df = pd.DataFrame({
        "Order Id": [1001, 1001, 1002],
        "Order Item Id": [1, 2, 3],
        "Category Name": ["Furniture", "Technology", "Furniture"],
        "Delivery Status": ["Late", "Late", "On Time"],
        "Customer Name": ["A Private Person", "A Private Person", "Another Person"],
    })
    audit = audit_order_grain(df)
    assert audit["unique_order_ids"] == 2
    assert audit["orders_with_multiple_rows"] == 1
    assert audit["orders_spanning_multiple_categories"] == 1
    assert "A Private Person" not in str(audit)
    assert "1001" not in str(audit)


def test_mismatching_order_status_audited_as_count():
    df = pd.DataFrame({"Order Id": [1, 1, 2], "Delivery Status": ["Late", "On Time", "Late"]})
    assert audit_order_grain(df)["orders_with_conflicting_non_null_delivery_statuses"] == 1
