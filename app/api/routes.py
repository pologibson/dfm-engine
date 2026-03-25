from typing import Dict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.workflow import WorkflowBlockingError, run_generation_from_bom_source, run_sample_generation
from app.models.schemas import GenerationResponse

router = APIRouter()


@router.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "DFM Auto Generator MVP is running.",
        "sample_endpoint": "/generate/sample",
        "upload_endpoint": "/generate",
    }


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/generate", response_model=GenerationResponse)
async def generate_ppt(
    step_file: UploadFile = File(...),
    bom_file: UploadFile = File(...),
    bom_profile: str = Form(default=""),
) -> GenerationResponse:
    step_bytes = await step_file.read()
    bom_bytes = await bom_file.read()
    try:
        result = run_generation_from_bom_source(
            step_filename=step_file.filename or "uploaded_model.step",
            step_bytes=step_bytes,
            bom_source_name=bom_file.filename or "uploaded_bom.json",
            bom_source_bytes=bom_bytes,
            bom_profile=bom_profile or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowBlockingError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(exc),
                "report_data_path": exc.report_data_path,
                "selected_bom_profile": exc.selected_bom_profile,
                "detected_bom_profile": exc.detected_bom_profile,
                "detected_bom_profile_confidence": exc.detected_bom_profile_confidence,
                "warnings": exc.warnings,
                "blocking_errors": exc.blocking_errors,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate PPT: {exc}") from exc
    return GenerationResponse(
        message="PPT generated successfully.",
        ppt_path=result.ppt_path,
        report_data_path=result.report_data_path,
        slide_count=result.slide_count,
        slide_titles=result.slide_titles,
        selected_bom_profile=result.selected_bom_profile,
        detected_bom_profile=result.detected_bom_profile,
        detected_bom_profile_confidence=result.detected_bom_profile_confidence,
        warnings=result.warnings,
        blocking_errors=result.blocking_errors,
    )


@router.post("/generate/sample", response_model=GenerationResponse)
def generate_sample_ppt(bom_profile: str = "") -> GenerationResponse:
    try:
        result = run_sample_generation(bom_profile=bom_profile or None)
    except WorkflowBlockingError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(exc),
                "report_data_path": exc.report_data_path,
                "selected_bom_profile": exc.selected_bom_profile,
                "detected_bom_profile": exc.detected_bom_profile,
                "detected_bom_profile_confidence": exc.detected_bom_profile_confidence,
                "warnings": exc.warnings,
                "blocking_errors": exc.blocking_errors,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate sample PPT: {exc}") from exc
    return GenerationResponse(
        message="Sample PPT generated successfully.",
        ppt_path=result.ppt_path,
        report_data_path=result.report_data_path,
        slide_count=result.slide_count,
        slide_titles=result.slide_titles,
        selected_bom_profile=result.selected_bom_profile,
        detected_bom_profile=result.detected_bom_profile,
        detected_bom_profile_confidence=result.detected_bom_profile_confidence,
        warnings=result.warnings,
        blocking_errors=result.blocking_errors,
    )
