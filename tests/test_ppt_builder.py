from pathlib import Path

from app.models.schemas import PresentationPlan, SlideSpec
from app.ppt_builder.builder import build_presentation


def test_ppt_builder_creates_output_file(tmp_path) -> None:
    plan = PresentationPlan(
        report_title="DFM Test Deck",
        subtitle="Builder smoke test",
        slides=[
            SlideSpec(
                index=1,
                title="DFM Auto-Generated Report",
                slide_type="cover",
                payload={
                    "subtitle": "Builder smoke test",
                    "report_meta": [["Product", "Unit Test"], ["CAD Parser", "Mock"]],
                    "stats": ["CAD parts: 5", "BOM items: 8", "Modules: 3"],
                    "image_kind": "overview",
                    "image_title": "Unit Test Product",
                    "image_labels": ["Motion", "Process", "Control"],
                },
            ),
            SlideSpec(
                index=2,
                title="DFM Workflow Overview",
                slide_type="process",
                payload={
                    "steps": ["STEP Mock", "BOM JSON", "Tagging", "Planning", "PPT Output"],
                    "image_kind": "workflow",
                    "image_title": "Workflow",
                    "image_labels": ["STEP Input", "BOM Import", "Tagging", "Planning", "PPT Export"],
                },
            ),
        ],
    )

    output_path = tmp_path / "builder_test.pptx"
    result_path = build_presentation(plan=plan, output_path=str(output_path))

    assert Path(result_path).exists()
    assert (tmp_path / "assets" / "builder_test").exists()
