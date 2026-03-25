from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from app.bom_adapter.config import get_fallback_profile, list_bom_profiles, load_bom_profile_config


def normalize_header(value: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in str(value).strip().lower())
    return "_".join(part for part in normalized.split("_") if part)


def collect_normalized_headers(records: Iterable[Dict[str, Any]]) -> Set[str]:
    headers = set()
    for record in records:
        headers.update(normalize_header(key) for key in record.keys())
    return headers


def _score_profile(
    profile_name: str,
    profile_config: Dict[str, Any],
    source_name: str,
    source_format: str,
    headers: Set[str],
) -> Dict[str, Any]:
    detection = profile_config.get("detection", {})
    extension = Path(source_name).suffix.lower()

    score = 0.0
    max_score = 0.0

    if profile_config.get("source_format") == source_format:
        score += 1.0
    max_score += 1.0

    preferred_extensions = detection.get("preferred_extensions", [])
    if preferred_extensions:
        if extension in preferred_extensions:
            score += 1.5
        max_score += 1.5

    header_keywords = [normalize_header(value) for value in detection.get("header_keywords", [])]
    if header_keywords:
        keyword_matches = sum(1 for keyword in header_keywords if keyword in headers)
        score += keyword_matches
        max_score += float(len(header_keywords))

    strong_header_groups = detection.get("strong_header_groups", [])
    for group in strong_header_groups:
        normalized_group = [normalize_header(value) for value in group]
        if normalized_group and all(value in headers for value in normalized_group):
            score += 2.5
        max_score += 2.5

    profile_kind = profile_config.get("profile_kind", "specialized")
    if profile_kind == "generic":
        score *= 0.75

    confidence = round(score / max_score, 4) if max_score else 0.0
    return {
        "profile_name": profile_name,
        "score": round(score, 4),
        "confidence": confidence,
        "profile_kind": profile_kind,
    }


def detect_bom_profile(
    records: List[Dict[str, Any]],
    source_name: str,
    source_format: str,
) -> Dict[str, Any]:
    """Lightweight profile detection based on source format and header patterns."""

    headers = collect_normalized_headers(records)
    scores = []
    for profile_name in list_bom_profiles():
        profile_config = load_bom_profile_config(profile_name)
        if profile_config.get("source_format") not in ("any", source_format):
            continue
        scores.append(_score_profile(profile_name, profile_config, source_name, source_format, headers))

    scores.sort(key=lambda item: item["score"], reverse=True)

    best_specialized = next((item for item in scores if item["profile_kind"] != "generic"), None)
    if best_specialized and best_specialized["confidence"] >= 0.4:
        detected_profile = best_specialized["profile_name"]
        selected_profile = detected_profile
        detection_matched = True
        confidence = best_specialized["confidence"]
    else:
        detected_profile = None
        selected_profile = get_fallback_profile(source_format)
        detection_matched = False
        confidence = round(best_specialized["confidence"], 4) if best_specialized else 0.0

    return {
        "selected_profile": selected_profile,
        "detected_profile": detected_profile,
        "confidence": confidence,
        "detection_matched": detection_matched,
        "candidate_scores": scores,
        "headers": sorted(headers),
    }


def resolve_bom_profile(
    records: List[Dict[str, Any]],
    source_name: str,
    source_format: str,
    bom_profile: Optional[str] = None,
) -> Dict[str, Any]:
    detection_result = detect_bom_profile(records=records, source_name=source_name, source_format=source_format)

    if bom_profile:
        load_bom_profile_config(bom_profile)
        detection_result["selected_profile"] = bom_profile

    detection_result["selected_profile_config"] = load_bom_profile_config(detection_result["selected_profile"])
    return detection_result
