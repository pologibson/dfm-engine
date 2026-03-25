from pathlib import Path

import pytest

from app.cad_parser.real_parser import FutureRealCADParser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GCAPP_SAMPLE_OUTPUT_DIR = PROJECT_ROOT / "data" / "gcapp_sample_output"


def _write_fake_gcapp_cli_script(script_path: Path, sample_model_path: Path, snapshot: bool = False) -> None:
    if snapshot:
        script_body = """#!/bin/sh
set -eu
output_dir=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$output_dir/snapshots"
printf 'fake-png' > "$output_dir/snapshots/overview.png"
"""
    else:
        script_body = """#!/bin/sh
set -eu
output_dir=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$output_dir"
cp "__MODEL_PATH__" "$output_dir/model.json"
""".replace("__MODEL_PATH__", str(sample_model_path))

    script_path.write_text(script_body, encoding="utf-8")
    script_path.chmod(0o755)


def test_real_parser_runs_gcapp_clis_and_adapts_output(tmp_path: Path) -> None:
    model_cli = tmp_path / "gcapp_cli"
    snapshot_cli = tmp_path / "gcapp_snapshot_cli"
    _write_fake_gcapp_cli_script(model_cli, GCAPP_SAMPLE_OUTPUT_DIR / "model.json")
    _write_fake_gcapp_cli_script(snapshot_cli, GCAPP_SAMPLE_OUTPUT_DIR / "model.json", snapshot=True)

    parser = FutureRealCADParser(
        gcapp_cli=str(model_cli),
        gcapp_snapshot_cli=str(snapshot_cli),
        gcapp_work_dir=tmp_path / "gcapp_runs",
    )

    cad_model = parser.parse(
        step_filename="robot_cell.step",
        step_bytes=b"ISO-10303-21;",
    )

    assert cad_model.source_file == "robot_cell.step"
    assert cad_model.product_name == "Robot Cell"
    assert cad_model.assembly_name == "Robot Cell Assembly"
    assert [part.part_no for part in cad_model.parts] == [
        "ASSY-001",
        "FRAME-001",
        "MOTION-001",
        "CTRL-001",
    ]
    assert cad_model.parts[1].parent_part_no == "ASSY-001"
    assert "overview" in cad_model.snapshot_assets
    assert Path(cad_model.snapshot_assets["overview"]).exists()
    assert cad_model.metadata["gcapp_mode"] == "cli"
    assert cad_model.metadata["gcapp_model_cli_invoked"] is True


def test_real_parser_builds_expected_gcapp_commands() -> None:
    parser = FutureRealCADParser(
        gcapp_cli="/opt/gcapp_cli",
        gcapp_snapshot_cli="/opt/gcapp_snapshot_cli",
    )

    model_command = parser.build_gcapp_command(
        step_path=Path("inputs/demo.step"),
        output_dir=Path("outputs/gcapp/demo"),
    )
    snapshot_command = parser.build_snapshot_command(
        step_path=Path("inputs/demo.step"),
        output_dir=Path("outputs/gcapp/demo"),
    )

    assert model_command == [
        "/opt/gcapp_cli",
        "--input",
        "inputs/demo.step",
        "--output-dir",
        "outputs/gcapp/demo",
    ]
    assert snapshot_command == [
        "/opt/gcapp_snapshot_cli",
        "--input",
        "inputs/demo.step",
        "--output-dir",
        "outputs/gcapp/demo",
    ]


def test_real_parser_supports_fallback_output_dir() -> None:
    parser = FutureRealCADParser(
        gcapp_cli="/missing/gcapp_cli",
        gcapp_snapshot_cli="/missing/gcapp_snapshot_cli",
        gcapp_output_dir=GCAPP_SAMPLE_OUTPUT_DIR,
    )

    cad_model = parser.parse(step_filename="robot_cell.step")

    assert cad_model.parts[0].part_no == "ASSY-001"
    assert cad_model.metadata["gcapp_mode"] == "fallback_output_dir"
    assert cad_model.snapshot_assets["overview"].endswith("overview.svg")


def test_real_parser_requires_cli_or_fallback_output_dir() -> None:
    parser = FutureRealCADParser(
        gcapp_cli="/missing/gcapp_cli",
        gcapp_snapshot_cli="/missing/gcapp_snapshot_cli",
    )

    with pytest.raises(RuntimeError, match="GCAPP model CLI is unavailable"):
        parser.parse(step_filename="robot_cell.step", step_bytes=b"ISO-10303-21;")
