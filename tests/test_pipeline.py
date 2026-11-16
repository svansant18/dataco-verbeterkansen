import pandas as pd
import pytest

import pipeline
from pipeline import StageCounts, validate_stage_counts
from test_dataco_kpis import raw_line


def test_pipeline_stage_conserves_rows():
    stage = StageCounts("remove_invalid", 10, 7, {"missing_order_id": 2, "bad_date": 1})
    assert validate_stage_counts(stage)
    assert stage.rows_excluded == 3


def test_pipeline_stage_fails_unexplained_drop():
    with pytest.raises(ValueError):
        validate_stage_counts(StageCounts("remove_invalid", 10, 7, {"missing_order_id": 2}))


def test_missing_values_are_excluded_with_one_reason_each_not_kept_silently():
    rows = [raw_line(1, 1), raw_line(2, 2), raw_line(3, 3)]
    rows[1]["Delivery Status"] = None   # ontbrekende verplichte waarde
    rows[2]["Order Id"] = None          # ontbrekende sleutel (en daardoor ook een ontbrekende waarde)
    valid, stage = pipeline.step_validate(pd.DataFrame(rows))
    # Een rij met twee problemen krijgt maar één reden: de eerste die past.
    assert stage.primary_exclusion_reasons == {"missing_order_or_line_id": 1, "missing_required_value": 1}
    assert len(valid) == 1
    assert validate_stage_counts(stage)


def test_analysis_columns_contain_no_personal_data():
    """Alleen deze kolommen worden uit de ruwe CSV ingelezen (usecols): persoonsgegevens komen nooit in het geheugen."""
    forbidden = ("customer", "email", "password", "fname", "lname", "street", "zipcode")
    assert not [c for c in pipeline.ANALYSIS_COLUMNS if any(f in c.lower() for f in forbidden)]
