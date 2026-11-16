import pandas as pd
import pytest
from pipeline import StageCounts, profile_schema, validate_stage_counts


def test_pipeline_stage_conserves_rows():
    stage = StageCounts("remove_invalid", 10, 7, {"missing_order_id": 2, "bad_date": 1})
    assert validate_stage_counts(stage)
    assert stage.rows_excluded == 3


def test_pipeline_stage_fails_unexplained_drop():
    with pytest.raises(ValueError):
        validate_stage_counts(StageCounts("remove_invalid", 10, 7, {"missing_order_id": 2}))


def test_schema_profile_contains_no_raw_identifiable_values():
    df = pd.DataFrame({"Customer Name": ["private-person"], "Order Id": [100]})
    report = profile_schema(df)
    assert report["rows"] == 1
    assert "private-person" not in str(report)
