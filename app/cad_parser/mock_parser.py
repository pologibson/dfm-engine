from pathlib import Path
from typing import Optional

from app.cad_parser.base import CADParser
from app.models.schemas import CADModel, CADPart, CADParserContract


class MockCADParser(CADParser):
    """Mock parser used by the MVP demo path.

    It returns a deterministic assembly tree so the rest of the DFM workflow
    can be demonstrated before a geometry-capable parser is connected.
    """

    contract = CADParserContract(
        parser_name="mock",
        accepted_input=[".step filename", "optional step bytes"],
        output_model="CADModel",
        required_output_fields=["source_file", "product_name", "assembly_name", "parts"],
        required_part_fields=["part_no", "part_name", "level", "parent_part_no", "module_hint", "notes"],
        notes="Does not read real geometry. Returns a stable demo assembly tree.",
    )

    def parse(self, step_filename: str, step_bytes: Optional[bytes] = None) -> CADModel:
        product_name = Path(step_filename).stem.replace("_", " ").title() or "Mock Product"

        parts = [
            CADPart(
                part_no="ASSY-001",
                part_name="Main Assembly",
                level=0,
                module_hint="system",
                notes="Top-level assembly parsed from mock STEP input.",
            ),
            CADPart(
                part_no="FRAME-001",
                part_name="Base Frame",
                level=1,
                parent_part_no="ASSY-001",
                module_hint="motion",
                notes="Welded structure and mounting datum.",
            ),
            CADPart(
                part_no="GANTRY-001",
                part_name="Gantry Motion Axis",
                level=1,
                parent_part_no="ASSY-001",
                module_hint="motion",
                notes="Carries linear rails, servo and ballscrew.",
            ),
            CADPart(
                part_no="TOOL-001",
                part_name="Process Head",
                level=1,
                parent_part_no="ASSY-001",
                module_hint="process",
                notes="Tooling or dispense module.",
            ),
            CADPart(
                part_no="CTRL-001",
                part_name="Electrical Cabinet",
                level=1,
                parent_part_no="ASSY-001",
                module_hint="control",
                notes="PLC, IO and power distribution.",
            ),
            CADPart(
                part_no="SAFE-001",
                part_name="Safety Enclosure",
                level=1,
                parent_part_no="ASSY-001",
                module_hint="safety",
                notes="Guarding and interlock interfaces.",
            ),
        ]

        return CADModel(
            source_file=step_filename,
            product_name=product_name,
            assembly_name=f"{product_name} Assembly",
            parts=parts,
        )
