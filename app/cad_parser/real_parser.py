from typing import Optional

from app.cad_parser.base import CADParser
from app.models.schemas import CADModel, CADParserContract


class FutureRealCADParser(CADParser):
    """Placeholder for a future production parser.

    Replace the body of `parse()` when a real STEP/assembly extraction engine is
    available. The return type must remain `CADModel` so downstream modules do
    not need to change.
    """

    contract = CADParserContract(
        parser_name="real",
        accepted_input=[".step filename", "raw STEP bytes"],
        output_model="CADModel",
        required_output_fields=["source_file", "product_name", "assembly_name", "parts"],
        required_part_fields=["part_no", "part_name", "level", "parent_part_no", "module_hint", "notes"],
        notes="Must extract a normalized assembly tree from a real STEP payload.",
    )

    def parse(self, step_filename: str, step_bytes: Optional[bytes] = None) -> CADModel:
        raise NotImplementedError(
            "Real STEP parsing is not implemented yet. "
            "Keep the same CADParser interface and return a CADModel when ready."
        )
