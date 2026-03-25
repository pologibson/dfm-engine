import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.bom_adapter.config import VALUE_NORMALIZATION_PATH, get_bom_profile_path
from app.bom_adapter.normalizer import normalize_mapped_values
from app.bom_adapter.profiles import normalize_header, resolve_bom_profile
from app.models.schemas import BOMAdaptationResult, NormalizedBOMPart


def _build_alias_lookup(field_aliases: Dict[str, List[str]]) -> Dict[str, List[str]]:
    return {
        canonical_field: sorted(
            set([normalize_header(canonical_field)] + [normalize_header(alias) for alias in aliases])
        )
        for canonical_field, aliases in field_aliases.items()
    }


def _extract_records_from_json(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]

    if isinstance(payload, dict):
        for candidate_key in ("items", "rows", "data", "bom", "records"):
            candidate = payload.get(candidate_key)
            if isinstance(candidate, list):
                return [record for record in candidate if isinstance(record, dict)]

    raise ValueError("BOM JSON must be a list of row objects or a dict containing items/rows/data.")


def _parse_source_records(source_name: str, source_bytes: bytes) -> Tuple[List[Dict[str, Any]], str]:
    extension = Path(source_name).suffix.lower()
    decoded = source_bytes.decode("utf-8-sig")

    if extension == ".csv":
        reader = csv.DictReader(io.StringIO(decoded))
        return [
            dict(row)
            for row in reader
            if any(str(value).strip() for value in row.values() if value is not None)
        ], "csv"

    if extension in (".json", ""):
        payload = json.loads(decoded)
        return _extract_records_from_json(payload), "json"

    raise ValueError("Unsupported BOM file format: {0}. Only JSON and CSV are supported.".format(extension or "unknown"))


def _parse_int(value: Any, default: int) -> int:
    if value is None or str(value).strip() == "":
        return default

    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _pick_value(
    normalized_record: Dict[str, Any],
    aliases: Dict[str, List[str]],
    canonical_field: str,
) -> Any:
    for alias in aliases.get(canonical_field, []):
        if alias in normalized_record and normalized_record[alias] not in (None, ""):
            return normalized_record[alias]
    return None


def _append_blocking_error(
    blocking_errors: List[str],
    row_index: int,
    message: str,
) -> None:
    blocking_errors.append("Row {0}: {1}".format(row_index, message))


def _append_warning(
    warnings: List[str],
    row_index: int,
    message: str,
) -> None:
    warnings.append("Row {0}: {1}".format(row_index, message))


def adapt_bom_records(
    records: List[Dict[str, Any]],
    source_name: str = "inline.json",
    source_format: str = "json",
    bom_profile: Optional[str] = None,
) -> BOMAdaptationResult:
    """Map external BOM rows into the internal normalized parts schema.

    The adapter now supports profile-based mapping, automatic profile detection,
    and a warning/blocking-error split so upstream input quality is visible
    without silently breaking downstream report generation.
    """

    profile_resolution = resolve_bom_profile(
        records=records,
        source_name=source_name,
        source_format=source_format,
        bom_profile=bom_profile,
    )
    profile_config = profile_resolution["selected_profile_config"]
    alias_lookup = _build_alias_lookup(profile_config["field_aliases"])
    defaults = profile_config["defaults"]
    critical_fields = set(profile_config.get("critical_fields", []))

    warnings = []
    blocking_errors = []
    normalized_parts = []

    for row_index, row in enumerate(records, start=1):
        normalized_record = {normalize_header(key): value for key, value in row.items()}

        mapped_values = {
            "item_no": _pick_value(normalized_record, alias_lookup, "item_no"),
            "part_name": _pick_value(normalized_record, alias_lookup, "part_name"),
            "quantity": _pick_value(normalized_record, alias_lookup, "quantity"),
            "uom": _pick_value(normalized_record, alias_lookup, "uom"),
            "material": _pick_value(normalized_record, alias_lookup, "material"),
            "process": _pick_value(normalized_record, alias_lookup, "process"),
            "category": _pick_value(normalized_record, alias_lookup, "category"),
            "supplier": _pick_value(normalized_record, alias_lookup, "supplier"),
            "lead_time_days": _pick_value(normalized_record, alias_lookup, "lead_time_days"),
            "module_hint": _pick_value(normalized_record, alias_lookup, "module_hint"),
            "is_spare": _pick_value(normalized_record, alias_lookup, "is_spare"),
            "is_consumable": _pick_value(normalized_record, alias_lookup, "is_consumable"),
            "revision": _pick_value(normalized_record, alias_lookup, "revision"),
            "drawing_no": _pick_value(normalized_record, alias_lookup, "drawing_no"),
            "notes": _pick_value(normalized_record, alias_lookup, "notes"),
        }
        normalized_value_result = normalize_mapped_values(
            mapped_values=mapped_values,
            defaults=defaults,
        )
        normalized_values = normalized_value_result["values"]
        for normalization_warning in normalized_value_result["warnings"]:
            _append_warning(warnings, row_index, normalization_warning)

        part_name_value = normalized_values["part_name"]
        quantity_value = normalized_values["quantity"]

        if "part_name" in critical_fields and part_name_value in (None, ""):
            _append_blocking_error(
                blocking_errors,
                row_index,
                "missing critical field part_name/name/item_name; default placeholder was assigned.",
            )

        if "quantity" in critical_fields and quantity_value in (None, ""):
            _append_blocking_error(
                blocking_errors,
                row_index,
                "missing critical field qty/quantity; default quantity=1 was assigned.",
            )
        elif "quantity" in critical_fields and _parse_int(quantity_value, defaults["quantity"]) <= 0:
            _append_blocking_error(
                blocking_errors,
                row_index,
                "quantity must be greater than 0.",
            )

        part_name = str(part_name_value or "Unnamed Part {0}".format(row_index))
        item_no = normalized_values["item_no"]
        if item_no in (None, ""):
            item_no = "AUTO-{0:03d}".format(row_index)
            _append_warning(warnings, row_index, "missing item number, defaulted to '{0}'.".format(item_no))

        if mapped_values["supplier"] in (None, ""):
            _append_warning(
                warnings,
                row_index,
                "missing vendor/supplier, defaulted to '{0}'.".format(defaults["supplier"]),
            )

        if mapped_values["lead_time_days"] in (None, ""):
            _append_warning(
                warnings,
                row_index,
                "missing lead_time/lt/leadtime, defaulted to {0} days.".format(defaults["lead_time_days"]),
            )

        if mapped_values["category"] in (None, ""):
            _append_warning(
                warnings,
                row_index,
                "missing category/type, defaulted to '{0}'.".format(defaults["category"]),
            )

        normalized_part = NormalizedBOMPart(
            item_no=str(item_no),
            part_name=part_name,
            quantity=_parse_int(quantity_value, defaults["quantity"]),
            uom=str(normalized_values["uom"] or defaults["uom"]),
            material=str(normalized_values["material"] or defaults["material"]),
            process=str(normalized_values["process"] or defaults["process"]),
            category=str(normalized_values["category"] or defaults["category"]),
            supplier=str(normalized_values["supplier"] or defaults["supplier"]),
            lead_time_days=int(normalized_values["lead_time_days"]),
            module_hint=normalized_values["module_hint"] or defaults["module_hint"],
            is_spare=bool(normalized_values["is_spare"]),
            is_consumable=bool(normalized_values["is_consumable"]),
            revision=str(normalized_values["revision"] or defaults["revision"]),
            drawing_no=str(normalized_values["drawing_no"] or defaults["drawing_no"]),
            notes=str(normalized_values["notes"] or defaults["notes"]),
            source_row=row_index,
            source_fields=row,
            raw_values=normalized_value_result["raw_values"],
            normalization_trace=normalized_value_result["trace"],
        )
        normalized_parts.append(normalized_part)

    return BOMAdaptationResult(
        source_name=source_name,
        source_format=source_format,
        selected_bom_profile=profile_resolution["selected_profile"],
        detected_bom_profile=profile_resolution["detected_profile"],
        detected_bom_profile_confidence=profile_resolution["confidence"],
        detection_matched=profile_resolution["detection_matched"],
        candidate_profile_scores=profile_resolution["candidate_scores"],
        mapping_path=str(get_bom_profile_path(profile_resolution["selected_profile"]).resolve()),
        normalization_config_path=str(VALUE_NORMALIZATION_PATH.resolve()),
        normalized_parts=normalized_parts,
        warnings=warnings,
        blocking_errors=blocking_errors,
    )


def adapt_bom_payload(
    bom_payload: Any,
    source_name: str = "inline.json",
    bom_profile: Optional[str] = None,
) -> BOMAdaptationResult:
    records = _extract_records_from_json(bom_payload)
    return adapt_bom_records(
        records=records,
        source_name=source_name,
        source_format="json",
        bom_profile=bom_profile,
    )


def adapt_bom_source(
    source_name: str,
    source_bytes: bytes,
    bom_profile: Optional[str] = None,
) -> BOMAdaptationResult:
    records, source_format = _parse_source_records(source_name=source_name, source_bytes=source_bytes)
    return adapt_bom_records(
        records=records,
        source_name=source_name,
        source_format=source_format,
        bom_profile=bom_profile,
    )
