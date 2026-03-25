# GCAPP Parser Contract

This document defines the handoff between the DFM engine and a future GCAPP
command-line parser. The DFM engine will keep its current workflow and only
swap the `real` CAD parser backend from a mock implementation to this adapter.

## Goal

Given a STEP file, GCAPP should generate:

- a normalized `model.json`
- a `snapshots/` directory containing rendered views or extracted images

The Python side will read those artifacts, validate them, and translate them
into the stable `CADModel` already used by tagging, planning, and PPT building.

## Expected CLI Interface

The adapter expects a CLI shaped like:

```bash
gcapp \
  --input-step /path/to/input.step \
  --output-model /path/to/output/model.json \
  --output-snapshots /path/to/output/snapshots
```

### Input

- `--input-step`
  - Absolute or relative path to a `.step` or `.stp` file

### Output

- `--output-model`
  - Path to a UTF-8 JSON file
  - File must exist when GCAPP exits successfully
- `--output-snapshots`
  - Path to a directory created by GCAPP
  - Snapshot files referenced from `model.json` must live under this directory

## `model.json` Schema

The Python adapter validates the artifact against the `ParsedModel` schema.

```json
{
  "source_file": "robot_cell.step",
  "product_name": "Robot Cell",
  "assembly_name": "Robot Cell Assembly",
  "root_node_id": "ASSY-ROOT",
  "nodes": [
    {
      "node_id": "ASSY-ROOT",
      "parent_node_id": null,
      "part_no": "ASSY-001",
      "part_name": "Main Assembly",
      "level": 0,
      "module_hint": "system",
      "notes": "Top-level assembly",
      "snapshot_ids": ["overview"],
      "attributes": {
        "native_name": "Main Assembly"
      }
    }
  ],
  "snapshots": [
    {
      "snapshot_id": "overview",
      "relative_path": "snapshots/overview.svg",
      "label": "Overall assembly view",
      "kind": "overview",
      "node_id": "ASSY-ROOT"
    }
  ],
  "metadata": {
    "generator": "gcapp-cli",
    "version": "0.1"
  }
}
```

## Node Expectations

Each node must include:

- `node_id`
- `part_no`
- `part_name`
- `level`

Optional but strongly recommended:

- `parent_node_id`
- `module_hint`
- `notes`
- `snapshot_ids`
- `attributes`

## Snapshot Expectations

Each snapshot must include:

- `snapshot_id`
- `relative_path`
- `label`

Optional:

- `kind`
- `node_id`

The adapter resolves `relative_path` from the GCAPP output directory and fails
fast if the referenced file is missing.

## Adapter Behavior

The DFM engine's `FutureRealCADParser`:

1. receives the STEP filename from the existing workflow
2. locates GCAPP output artifacts
3. validates `model.json` against `ParsedModel`
4. validates referenced snapshot files exist
5. adapts nodes into the stable `CADModel.parts` list

This is intentionally an adapter boundary only. No Python STEP geometry parsing
or GCAPP UI integration is part of this contract.
