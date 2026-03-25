import json
import os
from pathlib import Path
from typing import List, Optional

from app.cad_parser.base import CADParser
from app.models.schemas import CADModel, CADParserContract, CADPart, ParsedModel


class FutureRealCADParser(CADParser):
    """GCAPP CLI adapter stub for the real CAD integration path.

    This class intentionally keeps the workflow-facing contract unchanged:
    callers still receive a normalized `CADModel`. The real integration path is
    delegated to an external GCAPP CLI which is expected to emit a `model.json`
    file plus a snapshots directory. This stub currently validates and adapts
    those artifacts; it does not implement geometry parsing in Python.
    """

    contract = CADParserContract(
        parser_name="real",
        accepted_input=[".step filename", "raw STEP bytes"],
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
        external_artifacts=["model.json", "snapshots/"],
        notes=(
            "Adapter around the GCAPP CLI contract. Expects a STEP input, a "
            "generated model.json, and a snapshots directory, then maps them "
            "back to the stable CADModel consumed by the current workflow."
        ),
    )

    def __init__(
        self,
        gcapp_cli: Optional[str] = None,
        gcapp_output_dir: Optional[Path] = None,
    ) -> None:
        self.gcapp_cli = gcapp_cli or os.getenv("DFM_GCAPP_CLI", "gcapp")
        configured_output_dir = gcapp_output_dir or os.getenv("DFM_GCAPP_OUTPUT_DIR")
        self.gcapp_output_dir = Path(configured_output_dir).resolve() if configured_output_dir else None

    def parse(self, step_filename: str, step_bytes: Optional[bytes] = None) -> CADModel:
        """Load GCAPP artifacts and adapt them into the stable workflow model."""

        output_dir = self._require_output_dir(step_filename=step_filename)
        parsed_model = self._load_parsed_model(output_dir=output_dir)
        return self._to_cad_model(parsed_model=parsed_model, requested_step_filename=step_filename)

    def build_gcapp_command(self, step_path: Path, output_dir: Path) -> List[str]:
        """Return the expected GCAPP CLI invocation for a STEP file."""

        return [
            self.gcapp_cli,
            "--input-step",
            str(step_path),
            "--output-model",
            str(output_dir / "model.json"),
            "--output-snapshots",
            str(output_dir / "snapshots"),
        ]

    def _require_output_dir(self, step_filename: str) -> Path:
        if self.gcapp_output_dir is None:
            preview_output_dir = Path("outputs") / "gcapp" / Path(step_filename).stem
            preview_command = " ".join(
                self.build_gcapp_command(
                    step_path=Path(step_filename),
                    output_dir=preview_output_dir,
                )
            )
            raise RuntimeError(
                "GCAPP output directory is not configured. This adapter stub expects pre-generated "
                "GCAPP artifacts. Set DFM_GCAPP_OUTPUT_DIR or instantiate FutureRealCADParser with "
                "gcapp_output_dir. Expected CLI shape: {0}".format(preview_command)
            )

        if not self.gcapp_output_dir.exists():
            raise FileNotFoundError(
                "Configured GCAPP output directory does not exist: {0}".format(self.gcapp_output_dir)
            )

        return self.gcapp_output_dir

    def _load_parsed_model(self, output_dir: Path) -> ParsedModel:
        model_path = output_dir / "model.json"
        snapshots_dir = output_dir / "snapshots"

        if not model_path.exists():
            raise FileNotFoundError("GCAPP model.json not found: {0}".format(model_path))
        if not snapshots_dir.exists() or not snapshots_dir.is_dir():
            raise FileNotFoundError("GCAPP snapshots directory not found: {0}".format(snapshots_dir))

        payload = json.loads(model_path.read_text(encoding="utf-8"))
        parsed_model = ParsedModel.model_validate(payload)

        for snapshot in parsed_model.snapshots:
            snapshot_path = output_dir / snapshot.relative_path
            if not snapshot_path.exists():
                raise FileNotFoundError(
                    "GCAPP snapshot referenced by model.json is missing: {0}".format(snapshot_path)
                )

        return parsed_model

    def _to_cad_model(self, parsed_model: ParsedModel, requested_step_filename: str) -> CADModel:
        node_to_part_no = {node.node_id: node.part_no for node in parsed_model.nodes}
        parts = [
            CADPart(
                part_no=node.part_no,
                part_name=node.part_name,
                level=node.level,
                parent_part_no=node_to_part_no.get(node.parent_node_id) if node.parent_node_id else None,
                module_hint=node.module_hint,
                notes=node.notes,
            )
            for node in parsed_model.nodes
        ]

        return CADModel(
            source_file=requested_step_filename or parsed_model.source_file,
            product_name=parsed_model.product_name,
            assembly_name=parsed_model.assembly_name,
            parts=parts,
        )
