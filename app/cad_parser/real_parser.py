import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from app.cad_parser.base import CADParser
from app.models.schemas import (
    CADModel,
    CADParserContract,
    CADPart,
    GCAPPModelPayload,
    ParsedModel,
    ParsedNode,
    ParsedSnapshot,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FutureRealCADParser(CADParser):
    """Adapter around the external GCAPP CLI executables.

    The workflow still receives a stable `CADModel`. This adapter is
    responsible for:

    - materializing the STEP input for the CLI tools
    - calling `gcapp_cli` to produce `model.json`
    - calling `gcapp_snapshot_cli` to produce `snapshots/overview.png`
    - translating the lightweight GCAPP output into the richer internal model
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
        external_artifacts=["model.json", "snapshots/overview.png"],
        notes=(
            "Calls gcapp_cli for model.json and gcapp_snapshot_cli for overview "
            "imagery, then adapts the result back to the stable CADModel used by "
            "the current workflow."
        ),
    )

    def __init__(
        self,
        gcapp_cli: Optional[str] = None,
        gcapp_snapshot_cli: Optional[str] = None,
        gcapp_output_dir: Optional[Path] = None,
        gcapp_work_dir: Optional[Path] = None,
    ) -> None:
        self.gcapp_cli = gcapp_cli or os.getenv("DFM_GCAPP_CLI", "gcapp_cli")
        self.gcapp_snapshot_cli = gcapp_snapshot_cli or os.getenv(
            "DFM_GCAPP_SNAPSHOT_CLI",
            "gcapp_snapshot_cli",
        )

        configured_output_dir = gcapp_output_dir or os.getenv("DFM_GCAPP_OUTPUT_DIR")
        self.gcapp_output_dir = Path(configured_output_dir).resolve() if configured_output_dir else None

        configured_work_dir = gcapp_work_dir or os.getenv("DFM_GCAPP_WORK_DIR")
        self.gcapp_work_dir = (
            Path(configured_work_dir).resolve()
            if configured_work_dir
            else (PROJECT_ROOT / "outputs" / "gcapp_runs")
        )

    def parse(self, step_filename: str, step_bytes: Optional[bytes] = None) -> CADModel:
        """Parse a STEP payload by delegating to the configured GCAPP CLIs."""

        output_dir, execution_metadata = self._resolve_output_dir(
            step_filename=step_filename,
            step_bytes=step_bytes,
        )
        parsed_model = self._load_parsed_model(
            output_dir=output_dir,
            requested_step_filename=step_filename,
            execution_metadata=execution_metadata,
        )
        return self._to_cad_model(
            parsed_model=parsed_model,
            requested_step_filename=step_filename,
            output_dir=output_dir,
        )

    def build_gcapp_command(self, step_path: Path, output_dir: Path) -> List[str]:
        """Return the expected `gcapp_cli` invocation for model generation."""

        return [
            self.gcapp_cli,
            "--input",
            str(step_path),
            "--output-dir",
            str(output_dir),
        ]

    def build_snapshot_command(self, step_path: Path, output_dir: Path) -> List[str]:
        """Return the expected `gcapp_snapshot_cli` invocation."""

        return [
            self.gcapp_snapshot_cli,
            "--input",
            str(step_path),
            "--output-dir",
            str(output_dir),
        ]

    def _resolve_output_dir(
        self,
        step_filename: str,
        step_bytes: Optional[bytes],
    ) -> Tuple[Path, Dict[str, object]]:
        if self.gcapp_output_dir is not None:
            if not self.gcapp_output_dir.exists():
                raise FileNotFoundError(
                    "Configured GCAPP output directory does not exist: {0}".format(self.gcapp_output_dir)
                )

            return self.gcapp_output_dir, {
                "gcapp_mode": "fallback_output_dir",
                "gcapp_model_cli_invoked": False,
                "gcapp_snapshot_cli_invoked": False,
                "gcapp_output_dir": str(self.gcapp_output_dir.resolve()),
            }

        if not self._command_available(self.gcapp_cli):
            raise RuntimeError(
                "GCAPP model CLI is unavailable. Set DFM_GCAPP_CLI to the gcapp_cli executable "
                "or set DFM_GCAPP_OUTPUT_DIR to a pre-generated GCAPP output directory."
            )

        output_dir = self._create_run_output_dir(step_filename=step_filename)
        step_path = self._materialize_step_input(
            step_filename=step_filename,
            step_bytes=step_bytes,
            output_dir=output_dir,
        )

        self._run_cli(
            command=self.build_gcapp_command(step_path=step_path, output_dir=output_dir),
            cli_name="gcapp_cli",
        )

        snapshot_invoked = False
        snapshot_status = "unavailable"
        if self._command_available(self.gcapp_snapshot_cli):
            snapshot_invoked = True
            snapshot_status = "generated"
            try:
                self._run_cli(
                    command=self.build_snapshot_command(step_path=step_path, output_dir=output_dir),
                    cli_name="gcapp_snapshot_cli",
                )
            except RuntimeError:
                # Snapshot generation is additive and should not block structure parsing.
                snapshot_status = "failed"
        else:
            snapshot_status = "unavailable"

        return output_dir, {
            "gcapp_mode": "cli",
            "gcapp_model_cli_invoked": True,
            "gcapp_snapshot_cli_invoked": snapshot_invoked,
            "gcapp_snapshot_status": snapshot_status,
            "gcapp_output_dir": str(output_dir.resolve()),
            "gcapp_model_cli": self.gcapp_cli,
            "gcapp_snapshot_cli": self.gcapp_snapshot_cli,
        }

    def _create_run_output_dir(self, step_filename: str) -> Path:
        safe_stem = Path(step_filename).stem or "step_input"
        safe_stem = safe_stem.replace(" ", "_")
        output_dir = self.gcapp_work_dir / "{0}_{1}".format(safe_stem, uuid4().hex[:8])
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _materialize_step_input(
        self,
        step_filename: str,
        step_bytes: Optional[bytes],
        output_dir: Path,
    ) -> Path:
        step_path = output_dir / Path(step_filename).name
        if step_bytes is not None:
            step_path.write_bytes(step_bytes)
            return step_path

        source_path = Path(step_filename)
        if source_path.exists() and source_path.is_file():
            if source_path.resolve() != step_path.resolve():
                shutil.copyfile(source_path, step_path)
            return step_path

        raise FileNotFoundError(
            "STEP input is not available for GCAPP CLI execution: {0}".format(step_filename)
        )

    def _run_cli(self, command: List[str], cli_name: str) -> None:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise RuntimeError("Failed to execute {0}: {1}".format(cli_name, exc)) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "{0} failed with exit code {1}. stdout={2!r} stderr={3!r}".format(
                    cli_name,
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )
            )

    def _command_available(self, command: str) -> bool:
        if not command.strip():
            return False

        candidate = Path(command).expanduser()
        if candidate.is_absolute() or "/" in command or "\\" in command:
            return candidate.exists()

        return shutil.which(command) is not None

    def _load_parsed_model(
        self,
        output_dir: Path,
        requested_step_filename: str,
        execution_metadata: Dict[str, object],
    ) -> ParsedModel:
        model_path = output_dir / "model.json"
        if not model_path.exists():
            raise FileNotFoundError("GCAPP model.json not found: {0}".format(model_path))

        payload = GCAPPModelPayload.model_validate(
            json.loads(model_path.read_text(encoding="utf-8"))
        )
        root_node = self._find_root_node(payload=payload)
        product_name = self._derive_product_name(
            root_node_name=root_node.part_name if root_node is not None else None,
            step_filename=requested_step_filename,
        )

        parsed_nodes = [
            ParsedNode(
                node_id=self._resolve_node_id(node=node, fallback_prefix="node_{0}".format(index)),
                parent_node_id=node.parent_node_id or node.parent,
                part_no=node.part_no or self._resolve_node_id(node=node, fallback_prefix="node_{0}".format(index)),
                part_name=node.part_name or node.name or self._resolve_node_id(node=node, fallback_prefix="node_{0}".format(index)),
                level=node.level,
                module_hint=node.module_hint or ("system" if self._resolve_node_id(node=node, fallback_prefix="node_{0}".format(index)) == payload.root_node_id else None),
                notes=node.notes,
            )
            for index, node in enumerate(payload.nodes)
        ]

        if root_node is None:
            parsed_nodes.insert(
                0,
                ParsedNode(
                    node_id=payload.root_node_id,
                    part_no=payload.root_node_id,
                    part_name=product_name,
                    level=0,
                    module_hint="system",
                    notes="Synthetic root created by the dfm-engine GCAPP adapter.",
                ),
            )

        overview_snapshot = self._discover_overview_snapshot(output_dir=output_dir)
        snapshots = []
        if overview_snapshot is not None:
            snapshots.append(
                ParsedSnapshot(
                    snapshot_id="overview",
                    relative_path=overview_snapshot.relative_to(output_dir).as_posix(),
                    label="GCAPP Overview Snapshot",
                    kind="overview",
                    node_id=payload.root_node_id,
                )
            )

        metadata = dict(execution_metadata)
        metadata.update(
            {
                "gcapp_model_path": str(model_path.resolve()),
                "gcapp_root_node_id": payload.root_node_id,
                "gcapp_overview_snapshot_path": str(overview_snapshot.resolve()) if overview_snapshot else "",
            }
        )

        return ParsedModel(
            source_file=requested_step_filename,
            product_name=product_name,
            assembly_name="{0} Assembly".format(product_name),
            root_node_id=payload.root_node_id,
            nodes=parsed_nodes,
            snapshots=snapshots,
            metadata=metadata,
        )

    def _find_root_node(self, payload: GCAPPModelPayload):
        for node in payload.nodes:
            if self._resolve_node_id(node=node, fallback_prefix="root") == payload.root_node_id:
                return node
        return None

    def _resolve_node_id(self, node, fallback_prefix: str) -> str:
        return node.node_id or node.id or node.part_no or fallback_prefix

    def _derive_product_name(self, root_node_name: Optional[str], step_filename: str) -> str:
        fallback_name = Path(step_filename).stem.replace("_", " ").title() or "GCAPP Product"
        if not root_node_name:
            return fallback_name

        normalized_root = root_node_name.strip()
        if normalized_root.lower() in {"root", "assembly", "main assembly"}:
            return fallback_name

        return normalized_root

    def _discover_overview_snapshot(self, output_dir: Path) -> Optional[Path]:
        preferred_path = output_dir / "snapshots" / "overview.png"
        if preferred_path.exists():
            return preferred_path

        snapshots_dir = output_dir / "snapshots"
        if not snapshots_dir.exists() or not snapshots_dir.is_dir():
            return None

        candidates = sorted(snapshots_dir.glob("overview.*"))
        return candidates[0] if candidates else None

    def _to_cad_model(
        self,
        parsed_model: ParsedModel,
        requested_step_filename: str,
        output_dir: Path,
    ) -> CADModel:
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

        snapshot_assets = {
            snapshot.snapshot_id: str((output_dir / snapshot.relative_path).resolve())
            for snapshot in parsed_model.snapshots
        }

        return CADModel(
            source_file=requested_step_filename or parsed_model.source_file,
            product_name=parsed_model.product_name,
            assembly_name=parsed_model.assembly_name,
            parts=parts,
            snapshot_assets=snapshot_assets,
            metadata=dict(parsed_model.metadata),
        )
