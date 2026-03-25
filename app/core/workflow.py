import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.bom_adapter.adapter import adapt_bom_payload, adapt_bom_source
from app.cad_parser.parser import parse_step_file
from app.cad_parser.factory import get_cad_parser
from app.models.schemas import BOMAdaptationResult, BOMItem, GenerationResult, ReportData
from app.planner.service import create_presentation_plan
from app.ppt_builder.builder import build_presentation
from app.tagging.service import generate_tags

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WorkflowBlockingError(Exception):
    """Raised when BOM adaptation found blocking input issues."""

    def __init__(
        self,
        message: str,
        report_data_path: str,
        warnings: List[str],
        blocking_errors: List[str],
        selected_bom_profile: str,
        detected_bom_profile: Optional[str],
        detected_bom_profile_confidence: float,
    ) -> None:
        super().__init__(message)
        self.report_data_path = report_data_path
        self.warnings = warnings
        self.blocking_errors = blocking_errors
        self.selected_bom_profile = selected_bom_profile
        self.detected_bom_profile = detected_bom_profile
        self.detected_bom_profile_confidence = detected_bom_profile_confidence


def load_sample_payload() -> Dict[str, object]:
    """Load the bundled sample STEP and BOM inputs used by the demo flows."""

    step_path = PROJECT_ROOT / "data" / "mock_model.step"
    bom_path = PROJECT_ROOT / "data" / "mock_bom.json"
    return {
        "step_path": step_path,
        "step_bytes": step_path.read_bytes(),
        "bom_path": bom_path,
        "bom_bytes": bom_path.read_bytes(),
        "bom_payload": json.loads(bom_path.read_text(encoding="utf-8")),
    }


def _write_report_data(report_data: ReportData, output_path: Path) -> str:
    output_path.write_text(
        json.dumps(report_data.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(output_path.resolve())


def _build_report_data(
    generated_at: str,
    step_filename: str,
    parser_type: str,
    adaptation_result: BOMAdaptationResult,
    cad_model=None,
    tagging_result=None,
    plan=None,
) -> ReportData:
    parser = get_cad_parser(parser_type=parser_type)
    return ReportData(
        generated_at=generated_at,
        source={
            "step_filename": step_filename,
            "bom_source_name": adaptation_result.source_name,
            "bom_source_format": adaptation_result.source_format,
            "bom_mapping_path": adaptation_result.mapping_path,
            "cad_parser": parser_type,
            "cad_parser_contract": parser.get_contract().model_dump(),
            "profile_detection_matched": adaptation_result.detection_matched,
            "profile_candidate_scores": adaptation_result.candidate_profile_scores,
        },
        selected_bom_profile=adaptation_result.selected_bom_profile,
        detected_bom_profile=adaptation_result.detected_bom_profile,
        detected_bom_profile_confidence=adaptation_result.detected_bom_profile_confidence,
        warnings=adaptation_result.warnings,
        blocking_errors=adaptation_result.blocking_errors,
        parts=adaptation_result.normalized_parts,
        cad_model=cad_model.model_dump() if cad_model is not None else {},
        tagging=tagging_result.model_dump() if tagging_result is not None else {},
        plan_summary={
            "report_title": plan.report_title,
            "subtitle": plan.subtitle,
            "slide_count": len(plan.slides),
            "slide_titles": [slide.title for slide in plan.slides],
        } if plan is not None else {},
    )


def _run_generation_from_adaptation(
    step_filename: str,
    step_bytes: Optional[bytes],
    adaptation_result: BOMAdaptationResult,
    output_dir: str = "outputs",
    parser_type: Optional[str] = None,
) -> GenerationResult:
    resolved_parser_type = parser_type or "mock"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    output_stem = "dfm_report_{0}".format(timestamp)

    if adaptation_result.blocking_errors:
        report_data = _build_report_data(
            generated_at=datetime.now().isoformat(timespec="seconds"),
            step_filename=step_filename,
            parser_type=resolved_parser_type,
            adaptation_result=adaptation_result,
        )
        report_data_path = _write_report_data(
            report_data=report_data,
            output_path=output_dir_path / "{0}_report_data.json".format(output_stem),
        )
        raise WorkflowBlockingError(
            message="Blocking BOM validation errors found. See report_data.json for details.",
            report_data_path=report_data_path,
            warnings=adaptation_result.warnings,
            blocking_errors=adaptation_result.blocking_errors,
            selected_bom_profile=adaptation_result.selected_bom_profile,
            detected_bom_profile=adaptation_result.detected_bom_profile,
            detected_bom_profile_confidence=adaptation_result.detected_bom_profile_confidence,
        )

    bom_items = [
        BOMItem(**part.model_dump(exclude={"source_row", "source_fields"}))
        for part in adaptation_result.normalized_parts
    ]
    cad_model = parse_step_file(
        step_filename=step_filename,
        step_bytes=step_bytes,
        parser_type=resolved_parser_type,
    )
    tagging_result = generate_tags(cad_model=cad_model, bom_items=bom_items)
    plan = create_presentation_plan(
        cad_model=cad_model,
        bom_items=bom_items,
        tagging_result=tagging_result,
    )

    report_data = _build_report_data(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        step_filename=step_filename,
        parser_type=resolved_parser_type,
        adaptation_result=adaptation_result,
        cad_model=cad_model,
        tagging_result=tagging_result,
        plan=plan,
    )
    report_data_path = _write_report_data(
        report_data=report_data,
        output_path=output_dir_path / "{0}_report_data.json".format(output_stem),
    )

    output_path = output_dir_path / "{0}.pptx".format(output_stem)
    ppt_path = build_presentation(plan=plan, output_path=str(output_path))

    return GenerationResult(
        ppt_path=ppt_path,
        report_data_path=report_data_path,
        slide_count=len(plan.slides),
        slide_titles=[slide.title for slide in plan.slides],
        selected_bom_profile=adaptation_result.selected_bom_profile,
        detected_bom_profile=adaptation_result.detected_bom_profile,
        detected_bom_profile_confidence=adaptation_result.detected_bom_profile_confidence,
        warnings=adaptation_result.warnings,
        blocking_errors=adaptation_result.blocking_errors,
    )


def run_generation(
    step_filename: str,
    step_bytes: Optional[bytes],
    bom_payload: Any,
    output_dir: str = "outputs",
    parser_type: Optional[str] = None,
    bom_profile: Optional[str] = None,
    bom_source_name: str = "inline.json",
) -> GenerationResult:
    adaptation_result = adapt_bom_payload(
        bom_payload=bom_payload,
        source_name=bom_source_name,
        bom_profile=bom_profile,
    )
    return _run_generation_from_adaptation(
        step_filename=step_filename,
        step_bytes=step_bytes,
        adaptation_result=adaptation_result,
        output_dir=output_dir,
        parser_type=parser_type,
    )


def run_generation_from_bom_source(
    step_filename: str,
    step_bytes: Optional[bytes],
    bom_source_name: str,
    bom_source_bytes: bytes,
    output_dir: str = "outputs",
    parser_type: Optional[str] = None,
    bom_profile: Optional[str] = None,
) -> GenerationResult:
    adaptation_result = adapt_bom_source(
        source_name=bom_source_name,
        source_bytes=bom_source_bytes,
        bom_profile=bom_profile,
    )
    return _run_generation_from_adaptation(
        step_filename=step_filename,
        step_bytes=step_bytes,
        adaptation_result=adaptation_result,
        output_dir=output_dir,
        parser_type=parser_type,
    )


def run_sample_generation(
    output_dir: str = "outputs",
    parser_type: Optional[str] = None,
    bom_profile: Optional[str] = None,
) -> GenerationResult:
    """Generate the demo deck using bundled mock STEP + BOM inputs."""

    sample_payload = load_sample_payload()
    return run_generation_from_bom_source(
        step_filename=sample_payload["step_path"].name,
        step_bytes=sample_payload["step_bytes"],
        bom_source_name=sample_payload["bom_path"].name,
        bom_source_bytes=sample_payload["bom_bytes"],
        output_dir=output_dir,
        parser_type=parser_type,
        bom_profile=bom_profile,
    )
