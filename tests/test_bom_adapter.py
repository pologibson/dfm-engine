import json
from pathlib import Path

import pytest

from app.bom_adapter.adapter import adapt_bom_payload, adapt_bom_source
from app.core.workflow import WorkflowBlockingError, run_generation_from_bom_source

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_profile_manual_selection() -> None:
    payload = json.loads((PROJECT_ROOT / "data" / "realistic_bom.json").read_text(encoding="utf-8"))

    result = adapt_bom_payload(
        payload,
        source_name="realistic_bom.json",
        bom_profile="erp_style_a",
    )

    assert result.selected_bom_profile == "erp_style_a"
    assert result.mapping_path.endswith("erp_style_a.json")
    assert result.normalized_parts[0].part_name == "Base Weldment Assy"


def test_profile_auto_detection() -> None:
    csv_bytes = (PROJECT_ROOT / "data" / "realistic_bom.csv").read_bytes()

    result = adapt_bom_source("realistic_bom.csv", csv_bytes)

    assert result.detected_bom_profile == "erp_style_a"
    assert result.selected_bom_profile == "erp_style_a"
    assert result.detected_bom_profile_confidence >= 0.4


def test_warning_scenario_allows_generation(tmp_path) -> None:
    bom_payload = [
        {
            "item_name": "Cable Chain",
            "qty": 2,
            "remarks": "Vendor to be finalized."
        }
    ]

    result = run_generation_from_bom_source(
        step_filename="mock_model.step",
        step_bytes=(PROJECT_ROOT / "data" / "mock_model.step").read_bytes(),
        bom_source_name="warning_only.json",
        bom_source_bytes=json.dumps(bom_payload).encode("utf-8"),
        output_dir=str(tmp_path),
        bom_profile="generic_json",
    )

    report_data = json.loads(Path(result.report_data_path).read_text(encoding="utf-8"))

    assert Path(result.ppt_path).exists()
    assert report_data["warnings"]
    assert report_data["blocking_errors"] == []


def test_blocking_error_scenario_writes_report_data_and_stops(tmp_path) -> None:
    bom_payload = [
        {
            "line_no": "0090",
            "vendor": "Unknown",
            "remarks": "Description and quantity are missing."
        }
    ]

    with pytest.raises(WorkflowBlockingError) as exc_info:
        run_generation_from_bom_source(
            step_filename="mock_model.step",
            step_bytes=(PROJECT_ROOT / "data" / "mock_model.step").read_bytes(),
            bom_source_name="blocking_error.json",
            bom_source_bytes=json.dumps(bom_payload).encode("utf-8"),
            output_dir=str(tmp_path),
            bom_profile="generic_json",
        )

    exc = exc_info.value
    report_data_path = Path(exc.report_data_path)
    report_data = json.loads(report_data_path.read_text(encoding="utf-8"))

    assert report_data_path.exists()
    assert len(exc.blocking_errors) >= 2
    assert report_data["selected_bom_profile"] == "generic_json"
    assert len(report_data["blocking_errors"]) >= 2
