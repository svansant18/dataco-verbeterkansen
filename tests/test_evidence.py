"""Evidence contract tests; not a substitute for real DataCo KPI reconciliation."""
import pytest

from analysis.evidence import EvidenceRecord


def test_placeholder_evidence_remains_pending_without_data():
    record = EvidenceRecord("DV2", "OPS-01", ("Order Id", "Delivery Status"), "late / eligible", "unique_order")
    assert record.status == "PENDING"
    assert record.result is None
    assert record.as_display_metadata()["numerator"] is None


def test_cannot_claim_validated_without_real_source_and_tests():
    with pytest.raises(ValueError, match="Cannot mark"):
        EvidenceRecord("DV1", "FIN-01", ("Sales",), "SUM(Sales)", "order_line", result=100.0, status="VALIDATED")


def test_stage_numbers_must_reconcile():
    with pytest.raises(ValueError, match="Row accounting mismatch"):
        EvidenceRecord("DV3", "COM-01", ("Sales",), "mean", "order_line", input_rows=100, analysis_rows=90, excluded_rows=9)


def test_validated_record_needs_all_evidence_fields():
    record = EvidenceRecord(
        question_id="DV4", metric_id="RISK-01", source_columns=("Market", "Category Name"),
        formula="approved_rule(DV1,DV2,DV3)", grain="market_category",
        pipeline_steps=("clean", "aggregate", "prioritize"),
        input_rows=100, analysis_rows=95, excluded_rows=5,
        result=1.0, decision_id="D-001", code_function="analysis.prioritize",
        test_ids=("test_priority",), raw_sha256="a"*64,
        processed_sha256="b"*64, processed_file="data/processed/example.csv",
        status="VALIDATED",
    )
    public = record.as_display_metadata()
    assert public["status"] == "VALIDATED"
    assert "raw_sha256" not in public
    assert "processed_file" not in public
