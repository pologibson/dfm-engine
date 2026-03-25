import json
from pathlib import Path
from typing import Any, Dict, List


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"
LEGACY_MAPPING_PATH = CONFIG_ROOT / "bom_mapping.json"
BOM_PROFILES_DIR = CONFIG_ROOT / "bom_profiles"
FALLBACK_PROFILES = {
    "json": "generic_json",
    "csv": "generic_csv",
}


def list_bom_profiles() -> List[str]:
    """List available BOM profile names from the config directory."""

    if not BOM_PROFILES_DIR.exists():
        return []
    return sorted(path.stem for path in BOM_PROFILES_DIR.glob("*.json"))


def get_bom_profile_path(profile_name: str) -> Path:
    profile_path = BOM_PROFILES_DIR / "{0}.json".format(profile_name)
    if not profile_path.exists():
        raise ValueError(
            "Unknown BOM profile: {0}. Available profiles: {1}".format(
                profile_name,
                ", ".join(list_bom_profiles()) or "none",
            )
        )
    return profile_path


def load_bom_profile_config(profile_name: str) -> Dict[str, Any]:
    """Load a named BOM profile config."""

    return json.loads(get_bom_profile_path(profile_name).read_text(encoding="utf-8"))


def get_fallback_profile(source_format: str) -> str:
    return FALLBACK_PROFILES.get(source_format, "generic_json")


def load_bom_mapping_config(config_path: str = "") -> Dict[str, Any]:
    """Backward-compatible loader for the legacy single mapping file."""

    resolved_path = Path(config_path) if config_path else LEGACY_MAPPING_PATH
    return json.loads(resolved_path.read_text(encoding="utf-8"))
