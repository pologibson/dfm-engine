from abc import ABC, abstractmethod
from typing import Optional

from app.models.schemas import CADModel, CADParserContract


class CADParser(ABC):
    """Stable boundary for STEP parsing implementations.

    The rest of the workflow only depends on this interface. Today we ship a
    mock parser for demo stability; a future real parser can implement the same
    contract without changing tagging/planner/ppt_builder.

    Input contract:
    - Receives the STEP filename and optional raw file bytes
    - Implementations may use filename metadata, bytes, or both

    Output contract:
    - Must always return a `CADModel`
    - `CADModel.parts` must contain normalized `CADPart` entries
    - Each part must provide `part_no`, `part_name`, `level`, `parent_part_no`,
      `module_hint` and `notes`
    """

    contract = CADParserContract(
        parser_name="base",
        accepted_input=["step_filename", "step_bytes"],
        output_model="CADModel",
        required_output_fields=["source_file", "product_name", "assembly_name", "parts"],
        required_part_fields=["part_no", "part_name", "level", "parent_part_no", "module_hint", "notes"],
        notes="Return a normalized CADModel regardless of parser backend.",
    )

    @classmethod
    def get_contract(cls) -> CADParserContract:
        return cls.contract

    @abstractmethod
    def parse(self, step_filename: str, step_bytes: Optional[bytes] = None) -> CADModel:
        """Parse a STEP payload into a normalized CADModel."""
