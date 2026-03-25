from collections import Counter
from typing import Any, Dict, List

from app.models.schemas import BOMItem, CADModel, PresentationPlan, SlideSpec, TaggingResult

MODULE_HINT_MAP = {
    "Motion Module": "motion",
    "Process Module": "process",
    "Control Module": "control",
    "Safety Module": "safety",
}


def _module_detail_payload(
    module_name: str,
    module_items: List[str],
    bom_items: List[BOMItem],
) -> Dict[str, Any]:
    # This payload stays intentionally simple so future real parsers/renderers
    # can populate the same fields without changing ppt_builder.
    module_hint = MODULE_HINT_MAP.get(module_name, "")
    related_items = [
        item
        for item in bom_items
        if item.part_name in module_items or item.module_hint == module_hint
    ]
    rows = [["Part Name", "Qty", "Process", "Lead Time"]]
    for item in related_items[:5]:
        rows.append(
            [
                item.part_name,
                str(item.quantity),
                item.process,
                f"{item.lead_time_days} d",
            ]
        )

    if len(rows) == 1:
        rows.append(["Mock Item", "1", "TBD", "14 d"])

    return {
        "summary": [
            f"{module_name} contains {len(module_items)} tagged parts/items.",
            "This page is generated from keyword-based mock classification.",
            "DFM review focus: interfaces, assembly sequence and supplier readiness.",
        ],
        "table_rows": rows,
        "image_kind": "module",
        "image_title": module_name,
        "image_labels": module_items[:4],
    }


def create_presentation_plan(
    cad_model: CADModel,
    bom_items: List[BOMItem],
    tagging_result: TaggingResult,
) -> PresentationPlan:
    module_counter = Counter({module: len(items) for module, items in tagging_result.module_map.items()})
    top_modules = [name for name, _ in module_counter.most_common(3)]
    while len(top_modules) < 3:
        top_modules.append(f"Module {len(top_modules) + 1}")

    spare_and_consumables = [
        item for item in bom_items if item.is_spare or item.is_consumable
    ]
    llts = [item for item in bom_items if item.lead_time_days >= 28]
    bom_category_counter = Counter(item.category for item in bom_items)

    slides = [
        SlideSpec(
            index=1,
            title="DFM Auto-Generated Report",
            slide_type="cover",
            payload={
                "subtitle": f"{cad_model.product_name} | Mock STEP + BOM driven MVP",
                "report_meta": [
                    ["Product", cad_model.product_name],
                    ["Assembly", cad_model.assembly_name],
                    ["CAD Parser", "Mock parser via CADParser interface"],
                    ["Review Scope", "Structure / module / spare / LLT / software architecture"],
                ],
                "stats": [
                    f"CAD parts: {len(cad_model.parts)}",
                    f"BOM items: {len(bom_items)}",
                    f"Modules: {len(tagging_result.module_map)}",
                ],
                "image_kind": "overview",
                "image_title": cad_model.product_name,
                "image_labels": list(tagging_result.module_map.keys()),
            },
        ),
        SlideSpec(
            index=2,
            title="Input Snapshot",
            slide_type="bullets",
            payload={
                "bullets": [
                    f"STEP source: {cad_model.source_file}",
                    f"Assembly name: {cad_model.assembly_name}",
                    f"BOM lines: {len(bom_items)}",
                    "Current version uses mock CAD parsing and mock visual generation.",
                ],
                "image_kind": "overview",
                "image_title": "Input Snapshot",
                "image_labels": [part.part_name for part in cad_model.parts if part.level == 1],
            },
        ),
        SlideSpec(
            index=3,
            title="DFM Workflow Overview",
            slide_type="process",
            payload={
                "steps": ["STEP Mock", "BOM JSON", "Tagging", "Planning", "PPT Output"],
                "image_kind": "workflow",
                "image_title": "Workflow",
                "image_labels": ["STEP Input", "BOM Import", "Tagging", "Planning", "PPT Export"],
            },
        ),
        SlideSpec(
            index=4,
            title="Product Structure Diagram",
            slide_type="structure",
            payload={
                "root": cad_model.assembly_name,
                "children": [part.part_name for part in cad_model.parts if part.level == 1],
                "image_kind": "overview",
                "image_title": "Product Overview",
                "image_labels": [part.part_name for part in cad_model.parts if part.level == 1],
            },
        ),
        SlideSpec(
            index=5,
            title="Assembly Hierarchy",
            slide_type="table",
            payload={
                "headers": ["Level", "Part No", "Part Name", "Notes"],
                "rows": [
                    [str(part.level), part.part_no, part.part_name, part.notes]
                    for part in cad_model.parts
                ],
            },
        ),
        SlideSpec(
            index=6,
            title="Module Decomposition Overview",
            slide_type="module_overview",
            payload={
                "modules": [
                    {
                        "name": module_name,
                        "count": len(items),
                        "preview": ", ".join(items[:3]) if items else "No items",
                    }
                    for module_name, items in tagging_result.module_map.items()
                ],
                "image_kind": "overview",
                "image_title": "Module Overview",
                "image_labels": list(tagging_result.module_map.keys()),
            },
        ),
        SlideSpec(
            index=7,
            title=f"{top_modules[0]} Detail",
            slide_type="module_detail",
            payload=_module_detail_payload(
                top_modules[0],
                tagging_result.module_map.get(top_modules[0], []),
                bom_items,
            ),
        ),
        SlideSpec(
            index=8,
            title=f"{top_modules[1]} Detail",
            slide_type="module_detail",
            payload=_module_detail_payload(
                top_modules[1],
                tagging_result.module_map.get(top_modules[1], []),
                bom_items,
            ),
        ),
        SlideSpec(
            index=9,
            title=f"{top_modules[2]} Detail",
            slide_type="module_detail",
            payload=_module_detail_payload(
                top_modules[2],
                tagging_result.module_map.get(top_modules[2], []),
                bom_items,
            ),
        ),
        SlideSpec(
            index=10,
            title="BOM Summary",
            slide_type="table",
            payload={
                "headers": ["Category", "Count"],
                "rows": [[category, str(count)] for category, count in bom_category_counter.items()],
            },
        ),
        SlideSpec(
            index=11,
            title="Spare Parts And Consumables",
            slide_type="table",
            payload={
                "headers": ["Item", "Type", "Qty", "Supplier", "Lead Time"],
                "rows": [
                    [
                        item.part_name,
                        "Consumable" if item.is_consumable else "Spare",
                        str(item.quantity),
                        item.supplier,
                        f"{item.lead_time_days} d",
                    ]
                    for item in spare_and_consumables
                ] or [["No mock items", "-", "-", "-", "-"]],
            },
        ),
        SlideSpec(
            index=12,
            title="Long Lead Time Items",
            slide_type="table",
            payload={
                "headers": ["Item", "Qty", "Lead Time", "Supplier", "Risk"],
                "rows": [
                    [
                        item.part_name,
                        str(item.quantity),
                        f"{item.lead_time_days} d",
                        item.supplier,
                        "Early sourcing required",
                    ]
                    for item in llts
                ] or [["No LLT item", "-", "-", "-", "-"]],
            },
        ),
        SlideSpec(
            index=13,
            title="DFM Observations",
            slide_type="bullets",
            payload={
                "bullets": tagging_result.dfm_observations,
                "image_kind": "module",
                "image_title": "DFM Focus Areas",
                "image_labels": ["Interfaces", "Sourcing", "Assembly", "Service"],
            },
        ),
        SlideSpec(
            index=14,
            title="Software Architecture",
            slide_type="architecture",
            payload={
                "layers": [
                    "FastAPI API Layer",
                    "cad_parser -> tagging -> planner -> ppt_builder",
                    "Mock STEP / BOM Input",
                    "PPTX Output",
                ],
                "image_kind": "software_architecture",
                "image_title": "Software Architecture",
                "image_labels": [
                    "FastAPI API Layer",
                    "cad_parser -> tagging -> planner -> ppt_builder",
                    "Input Adapters",
                    "PPTX Output",
                ],
            },
        ),
        SlideSpec(
            index=15,
            title="Next Steps",
            slide_type="bullets",
            payload={
                "bullets": [
                    "Replace mock STEP parser with a real CAD/assembly extractor.",
                    "Add geometry-based DFM rules for machining, sheet metal and assembly clearance.",
                    "Integrate template control, branding and richer chart/image rendering.",
                ]
            },
        ),
    ]

    return PresentationPlan(
        report_title="DFM Auto-Generated Report",
        subtitle=f"{cad_model.product_name} MVP deck",
        slides=slides,
    )
