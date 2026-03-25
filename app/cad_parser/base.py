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

    Real-parser boundary:
    - A production adapter may call external CLI tools such as GCAPP
    - The external tools may first emit a lightweight model.json plus snapshots
    - The adapter may normalize those artifacts into an intermediate `ParsedModel`
    - The adapter is responsible for validating that intermediate payload and
      translating it back into the stable `CADModel` used by the workflow
    """

    contract = CADParserContract(
        parser_name="base",
        accepted_input=["step_filename", "step_bytes"],
        output_model="CADModel",
        intermediate_model="ParsedModel",
        required_output_fields=["source_file", "product_name", "assembly_name", "parts"],
        required_part_fields=["part_no", "part_name", "level", "parent_part_no", "module_hint", "notes"],
        required_intermediate_fields=[
            "source_file",
            "product_name",
            "assembly_name",
            "root_node_id",
            "nodes",
            "snapshots",
        ],
        external_artifacts=["model.json", "snapshots/overview.png"],
        notes="Return a normalized CADModel regardless of parser backend.",
    )

    @classmethod
    def get_contract(cls) -> CADParserContract:
        return cls.contract

    @abstractmethod
    def parse(self, step_filename: str, step_bytes: Optional[bytes] = None) -> CADModel:
        """Parse a STEP payload into a normalized CADModel."""
