from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BOMItem(BaseModel):
    item_no: str
    part_name: str
    quantity: int = 1
    uom: str = "EA"
    material: str = "N/A"
    process: str = "N/A"
    category: str = "standard"
    supplier: str = "Mock Supplier"
    lead_time_days: int = 14
    module_hint: Optional[str] = None
    is_spare: bool = False
    is_consumable: bool = False
    revision: str = "N/A"
    drawing_no: str = "N/A"
    notes: str = ""


class NormalizedBOMPart(BOMItem):
    source_row: int
    source_fields: Dict[str, Any] = Field(default_factory=dict)
    raw_values: Dict[str, Any] = Field(default_factory=dict)
    normalization_trace: Dict[str, str] = Field(default_factory=dict)


class BOMAdaptationResult(BaseModel):
    source_name: str
    source_format: str
    selected_bom_profile: str
    detected_bom_profile: Optional[str] = None
    detected_bom_profile_confidence: float = 0.0
    detection_matched: bool = False
    candidate_profile_scores: List[Dict[str, Any]] = Field(default_factory=list)
    mapping_path: str
    normalization_config_path: str = ""
    normalized_parts: List[NormalizedBOMPart] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    blocking_errors: List[str] = Field(default_factory=list)


class CADPart(BaseModel):
    part_no: str
    part_name: str
    level: int = 0
    parent_part_no: Optional[str] = None
    module_hint: Optional[str] = None
    notes: str = ""


class CADModel(BaseModel):
    source_file: str
    product_name: str
    assembly_name: str
    parts: List[CADPart] = Field(default_factory=list)
    snapshot_assets: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GCAPPNodePayload(BaseModel):
    id: Optional[str] = None
    node_id: Optional[str] = None
    name: Optional[str] = None
    part_name: Optional[str] = None
    level: int = 0
    parent: Optional[str] = None
    parent_node_id: Optional[str] = None
    part_no: Optional[str] = None
    module_hint: Optional[str] = None
    notes: str = ""


class GCAPPModelPayload(BaseModel):
    root_node_id: str
    nodes: List[GCAPPNodePayload] = Field(default_factory=list)


class ParsedSnapshot(BaseModel):
    snapshot_id: str
    relative_path: str
    label: str
    kind: str = "general"
    node_id: Optional[str] = None


class ParsedNode(BaseModel):
    node_id: str
    parent_node_id: Optional[str] = None
    part_no: str
    part_name: str
    level: int = 0
    module_hint: Optional[str] = None
    notes: str = ""
    snapshot_ids: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ParsedModel(BaseModel):
    source_file: str
    product_name: str
    assembly_name: str
    root_node_id: str
    nodes: List[ParsedNode] = Field(default_factory=list)
    snapshots: List[ParsedSnapshot] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CADParserContract(BaseModel):
    parser_name: str
    accepted_input: List[str] = Field(default_factory=list)
    output_model: str = "CADModel"
    intermediate_model: str = ""
    required_output_fields: List[str] = Field(default_factory=list)
    required_part_fields: List[str] = Field(default_factory=list)
    required_intermediate_fields: List[str] = Field(default_factory=list)
    external_artifacts: List[str] = Field(default_factory=list)
    notes: str = ""


class TaggingResult(BaseModel):
    module_map: Dict[str, List[str]] = Field(default_factory=dict)
    keyword_tags: Dict[str, List[str]] = Field(default_factory=dict)
    dfm_observations: List[str] = Field(default_factory=list)


class SlideSpec(BaseModel):
    index: int
    title: str
    slide_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class PresentationPlan(BaseModel):
    report_title: str
    subtitle: str
    slides: List[SlideSpec] = Field(default_factory=list)


class ReportData(BaseModel):
    generated_at: str
    source: Dict[str, Any] = Field(default_factory=dict)
    selected_bom_profile: str = ""
    detected_bom_profile: Optional[str] = None
    detected_bom_profile_confidence: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    blocking_errors: List[str] = Field(default_factory=list)
    parts: List[NormalizedBOMPart] = Field(default_factory=list)
    cad_model: Dict[str, Any] = Field(default_factory=dict)
    tagging: Dict[str, Any] = Field(default_factory=dict)
    plan_summary: Dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    ppt_path: str
    report_data_path: str
    slide_count: int
    slide_titles: List[str]
    selected_bom_profile: str = ""
    detected_bom_profile: Optional[str] = None
    detected_bom_profile_confidence: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    blocking_errors: List[str] = Field(default_factory=list)


class GenerationResponse(BaseModel):
    message: str
    ppt_path: str
    report_data_path: str
    slide_count: int
    slide_titles: List[str]
    selected_bom_profile: str = ""
    detected_bom_profile: Optional[str] = None
    detected_bom_profile_confidence: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    blocking_errors: List[str] = Field(default_factory=list)
