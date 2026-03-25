from pathlib import Path

import pytest

from app.cad_parser.real_parser import FutureRealCADParser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GCAPP_SAMPLE_OUTPUT_DIR = PROJECT_ROOT / "data" / "gcapp_sample_output"


def test_real_parser_stub_adapts_fake_gcapp_output() -> None:
    parser = FutureRealCADParser(gcapp_output_dir=GCAPP_SAMPLE_OUTPUT_DIR)

    cad_model = parser.parse(step_filename="robot_cell.step")

    assert cad_model.source_file == "robot_cell.step"
    assert cad_model.product_name == "GCAPP Demo Cell"
    assert cad_model.assembly_name == "GCAPP Demo Cell Assembly"
    assert [part.part_no for part in cad_model.parts] == [
        "ASSY-001",
        "FRAME-001",
        "MOTION-001",
        "CTRL-001",
    ]
    assert cad_model.parts[1].parent_part_no == "ASSY-001"


def test_real_parser_stub_builds_expected_gcapp_command() -> None:
    parser = FutureRealCADParser(gcapp_cli="gcapp-cli")

    command = parser.build_gcapp_command(
        step_path=Path("inputs/demo.step"),
        output_dir=Path("outputs/gcapp/demo"),
    )

    assert command == [
        "gcapp-cli",
        "--input-step",
        "inputs/demo.step",
        "--output-model",
        "outputs/gcapp/demo/model.json",
        "--output-snapshots",
        "outputs/gcapp/demo/snapshots",
    ]


def test_real_parser_stub_requires_output_dir_configuration() -> None:
    parser = FutureRealCADParser(gcapp_cli="gcapp-cli")

    with pytest.raises(RuntimeError, match="GCAPP output directory is not configured"):
        parser.parse(step_filename="inputs/demo.step")
