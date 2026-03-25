import re
from typing import Any, Dict, List, Optional, Tuple

from app.bom_adapter.config import VALUE_NORMALIZATION_PATH, load_value_normalization_config


def _normalize_token(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.strip().lower(), flags=re.UNICODE)


def _clean_string(value: Any, null_like_values: List[str]) -> Optional[str]:
    if value is None:
        return None

    text = str(value).replace("\u3000", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None

    if _normalize_token(text) in {_normalize_token(item) for item in null_like_values}:
        return None
    return text


def _normalize_by_alias(
    value: Optional[str],
    aliases: Dict[str, List[str]],
    unknown_strategy: str = "preserve",
) -> Tuple[Optional[str], str]:
    if value is None:
        return None, "null"

    normalized_value = _normalize_token(value)
    for canonical, alias_values in aliases.items():
        candidates = [_normalize_token(canonical)] + [_normalize_token(alias) for alias in alias_values]
        if normalized_value in candidates:
            return canonical, "alias_map"

    if unknown_strategy == "uppercase":
        return value.upper(), "uppercase_fallback"
    if unknown_strategy == "lower":
        return value.lower(), "lower_fallback"
    return value, "preserve_fallback"


def _normalize_revision(value: Optional[str], config: Dict[str, Any]) -> Tuple[str, str]:
    if value is None:
        return config["default"], "default"

    cleaned = value
    for prefix in config.get("strip_prefixes", []):
        prefix_pattern = re.compile(r"^{0}\s*[:\-]?\s*".format(re.escape(prefix)), re.IGNORECASE)
        cleaned = prefix_pattern.sub("", cleaned).strip()

    if not cleaned:
        return config["default"], "default"

    if config.get("uppercase", False):
        return cleaned.upper(), "uppercase"
    return cleaned, "clean_only"


def _normalize_boolean(value: Any, config: Dict[str, Any], default: bool) -> Tuple[bool, str, Optional[str]]:
    if value is None:
        return default, "default", None

    normalized = _normalize_token(str(value))
    true_values = {_normalize_token(item) for item in config.get("true_values", [])}
    false_values = {_normalize_token(item) for item in config.get("false_values", [])}

    if normalized in true_values:
        return True, "boolean_true_map", None
    if normalized in false_values:
        return False, "boolean_false_map", None

    warning = "unrecognized boolean value '{0}', defaulted to {1}.".format(value, default)
    return default, "boolean_default", warning


def _parse_lead_time_days(value: Any, config: Dict[str, Any]) -> Tuple[int, str, Optional[str]]:
    default_days = int(config.get("default_days", 14))
    if value is None:
        return default_days, "default", None

    cleaned = str(value).strip().lower()
    if not cleaned:
        return default_days, "default", None

    exact_aliases = {_normalize_token(key): int(days) for key, days in config.get("exact_aliases", {}).items()}
    normalized = _normalize_token(cleaned)
    if normalized in exact_aliases:
        return exact_aliases[normalized], "exact_alias", None

    compound_match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", cleaned)
    if compound_match:
        numeric_value = float(compound_match.group(1))
        unit_token = compound_match.group(2).lower()
        for unit, multiplier in config.get("unit_days", {}).items():
            if unit_token == unit or unit_token.startswith(unit):
                return max(1, int(round(numeric_value * int(multiplier)))), "unit_parse", None

    number_match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not number_match:
        warning = "could not parse lead time '{0}', defaulted to {1} days.".format(value, default_days)
        return default_days, "default_unparsed", warning

    numeric_value = float(number_match.group(1))
    unit_days = config.get("unit_days", {})
    for unit, multiplier in unit_days.items():
        if re.search(r"\b{0}\b".format(re.escape(unit)), cleaned):
            return max(1, int(round(numeric_value * int(multiplier)))), "unit_parse", None

    return max(1, int(round(numeric_value))), "numeric_only", None


def normalize_mapped_values(
    mapped_values: Dict[str, Any],
    defaults: Dict[str, Any],
    normalization_config_path: str = "",
) -> Dict[str, Any]:
    """Normalize mapped BOM values before internal schema creation.

    This keeps value cleaning and canonicalization in one place so adapter code
    stays focused on field mapping and validation.
    """

    config = load_value_normalization_config(normalization_config_path)
    null_like_values = config.get("null_like_values", [])

    cleaned_values = {}
    raw_values = {}
    trace = {}
    warnings = []

    tracked_fields = (
        "item_no",
        "part_name",
        "quantity",
        "uom",
        "material",
        "process",
        "category",
        "supplier",
        "lead_time_days",
        "module_hint",
        "is_spare",
        "is_consumable",
        "revision",
        "drawing_no",
        "notes",
    )

    for field_name in tracked_fields:
        raw_values[field_name] = mapped_values.get(field_name)

    cleaned_values["item_no"] = _clean_string(mapped_values.get("item_no"), null_like_values)
    trace["item_no"] = "clean_string"

    cleaned_values["part_name"] = _clean_string(mapped_values.get("part_name"), null_like_values)
    trace["part_name"] = "clean_string"

    cleaned_values["quantity"] = _clean_string(mapped_values.get("quantity"), null_like_values)
    trace["quantity"] = "clean_string"

    cleaned_values["material"] = _clean_string(mapped_values.get("material"), null_like_values) or defaults["material"]
    trace["material"] = "clean_string"

    cleaned_values["process"] = _clean_string(mapped_values.get("process"), null_like_values) or defaults["process"]
    trace["process"] = "clean_string"

    uom_value, uom_rule = _normalize_by_alias(
        _clean_string(mapped_values.get("uom"), null_like_values),
        config.get("uom", {}).get("aliases", {}),
        config.get("uom", {}).get("unknown_strategy", "uppercase"),
    )
    cleaned_values["uom"] = uom_value or defaults["uom"]
    trace["uom"] = uom_rule

    supplier_value, supplier_rule = _normalize_by_alias(
        _clean_string(mapped_values.get("supplier"), null_like_values),
        config.get("supplier", {}).get("aliases", {}),
        config.get("supplier", {}).get("unknown_strategy", "preserve"),
    )
    cleaned_values["supplier"] = supplier_value or defaults["supplier"]
    trace["supplier"] = supplier_rule

    category_value, category_rule = _normalize_by_alias(
        _clean_string(mapped_values.get("category"), null_like_values),
        config.get("category", {}).get("aliases", {}),
        config.get("category", {}).get("unknown_strategy", "lower"),
    )
    cleaned_values["category"] = category_value or defaults["category"]
    trace["category"] = category_rule

    lead_time_value, lead_time_rule, lead_time_warning = _parse_lead_time_days(
        _clean_string(mapped_values.get("lead_time_days"), null_like_values),
        config.get("lead_time", {}),
    )
    cleaned_values["lead_time_days"] = lead_time_value
    trace["lead_time_days"] = lead_time_rule
    if lead_time_warning:
        warnings.append(lead_time_warning)

    cleaned_values["module_hint"] = _clean_string(mapped_values.get("module_hint"), null_like_values) or defaults["module_hint"]
    trace["module_hint"] = "clean_string"

    revision_value, revision_rule = _normalize_revision(
        _clean_string(mapped_values.get("revision"), null_like_values),
        config.get("revision", {}),
    )
    cleaned_values["revision"] = revision_value or defaults["revision"]
    trace["revision"] = revision_rule

    cleaned_values["drawing_no"] = _clean_string(mapped_values.get("drawing_no"), null_like_values) or defaults["drawing_no"]
    trace["drawing_no"] = "clean_string"

    cleaned_values["notes"] = _clean_string(mapped_values.get("notes"), null_like_values) or defaults["notes"]
    trace["notes"] = "clean_string"

    is_spare_value, is_spare_rule, is_spare_warning = _normalize_boolean(
        mapped_values.get("is_spare"),
        config.get("boolean_flags", {}),
        defaults["is_spare"],
    )
    cleaned_values["is_spare"] = is_spare_value
    trace["is_spare"] = is_spare_rule
    if is_spare_warning:
        warnings.append(is_spare_warning)

    is_consumable_value, is_consumable_rule, is_consumable_warning = _normalize_boolean(
        mapped_values.get("is_consumable"),
        config.get("boolean_flags", {}),
        defaults["is_consumable"],
    )
    cleaned_values["is_consumable"] = is_consumable_value
    trace["is_consumable"] = is_consumable_rule
    if is_consumable_warning:
        warnings.append(is_consumable_warning)

    return {
        "values": cleaned_values,
        "raw_values": raw_values,
        "trace": trace,
        "warnings": warnings,
        "config_path": normalization_config_path or str(VALUE_NORMALIZATION_PATH.resolve()),
    }
