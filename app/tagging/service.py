from collections import defaultdict
from typing import DefaultDict, List, Optional

from app.models.schemas import BOMItem, CADModel, TaggingResult

MODULE_RULES = {
    "Motion Module": ["frame", "gantry", "rail", "motor", "ballscrew", "screw", "belt", "axis"],
    "Process Module": ["tool", "fixture", "nozzle", "gripper", "process", "head"],
    "Control Module": ["plc", "sensor", "vision", "cable", "cabinet", "io", "hmi"],
    "Safety Module": ["safety", "guard", "interlock", "estop", "enclosure"],
}


def _resolve_module(name: str, module_hint: Optional[str] = None) -> str:
    normalized = name.lower()
    if module_hint:
        hint = module_hint.lower()
        if hint == "motion":
            return "Motion Module"
        if hint == "process":
            return "Process Module"
        if hint == "control":
            return "Control Module"
        if hint == "safety":
            return "Safety Module"

    for module_name, keywords in MODULE_RULES.items():
        if any(keyword in normalized for keyword in keywords):
            return module_name
    return "General Module"


def generate_tags(cad_model: CADModel, bom_items: List[BOMItem]) -> TaggingResult:
    module_map = defaultdict(list)  # type: DefaultDict[str, List[str]]
    keyword_tags = defaultdict(list)  # type: DefaultDict[str, List[str]]

    for part in cad_model.parts:
        if part.level == 0:
            keyword_tags[part.part_name] = ["root_assembly", "cad_mock"]
            continue
        module_name = _resolve_module(part.part_name, part.module_hint)
        module_map[module_name].append(part.part_name)
        keyword_tags[part.part_name] = [module_name, "cad_mock"]

    for item in bom_items:
        module_name = _resolve_module(item.part_name, item.module_hint)
        module_map[module_name].append(item.part_name)
        item_tags = [module_name, item.category]
        if item.is_spare:
            item_tags.append("spare")
        if item.is_consumable:
            item_tags.append("consumable")
        keyword_tags[item.part_name] = item_tags

    llt_items = [item.part_name for item in bom_items if item.lead_time_days >= 28]
    consumable_count = sum(1 for item in bom_items if item.is_consumable)
    spare_count = sum(1 for item in bom_items if item.is_spare)

    observations = [
        f"Detected {len(module_map)} logical modules from CAD + BOM mock tagging.",
        f"Found {len(llt_items)} long lead time items that should be tracked early.",
        f"Spare parts count: {spare_count}; consumables count: {consumable_count}.",
        "Current CAD parsing is mocked, so geometry-driven manufacturability checks are placeholders.",
    ]

    return TaggingResult(
        module_map=dict(module_map),
        keyword_tags=dict(keyword_tags),
        dfm_observations=observations,
    )
