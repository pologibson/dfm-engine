# GCAPP Parser Contract

This document defines the adapter boundary between `dfm-engine` and the GCAPP
command-line tools. The Python workflow keeps the same `CADParser -> CADModel`
contract; only the `real` parser backend changes.

## Goal

Given a STEP file, GCAPP should provide:

- `gcapp_cli`: structure extraction into `model.json`
- `gcapp_snapshot_cli`: rendered overview snapshot into `snapshots/overview.png`

The Python side is responsible for:

1. materializing the STEP input for the CLIs
2. invoking both executables
3. validating the generated artifacts
4. mapping the result back into the stable `CADModel` used by the workflow

## Expected CLI Interface

### Structure CLI

```bash
gcapp_cli \
  --input /path/to/input.step \
  --output-dir /path/to/output
```

Expected output:

- `/path/to/output/model.json`

### Snapshot CLI

```bash
gcapp_snapshot_cli \
  --input /path/to/input.step \
  --output-dir /path/to/output
```

Expected output:

- `/path/to/output/snapshots/overview.png`

The two executables are intentionally separate so the dfm-engine adapter can
keep structure parsing and snapshot generation loosely coupled.

## `model.json` Schema

`gcapp_cli` is expected to emit a lightweight assembly tree:

```json
{
  "root_node_id": "0:1",
  "nodes": [
    {
      "id": "0:1",
      "name": "ROOT",
      "level": 0,
      "parent": null
    },
    {
      "id": "0:1:1",
      "name": "Main Assembly",
      "level": 1,
      "parent": "0:1"
    },
    {
      "id": "123",
      "name": "Base Frame",
      "level": 2,
      "parent": "0:1:1"
    }
  ]
}
```

Minimum required fields:

- top-level `root_node_id`
- top-level `nodes`
- for each node:
  - `id`
  - `name`
  - `level`
  - `parent`

## Python-Side Normalization

The adapter accepts the lightweight CLI JSON and normalizes it into the richer
internal `ParsedModel`/`CADModel` shape used by the current workflow.

Normalization rules:

- `part_no` defaults to the GCAPP node `id`
- `part_name` defaults to the GCAPP node `name`
- `parent_part_no` is resolved from the node `parent`
- `product_name` is derived from the root node or STEP filename
- if `snapshots/overview.png` exists, it is attached as the `overview` asset

This keeps planner, tagging, PPT generation, API, and CLI entrypoints unchanged.

## Adapter Configuration

The `FutureRealCADParser` supports these environment variables:

- `DFM_GCAPP_CLI`
  - Absolute path or command name for `gcapp_cli`
- `DFM_GCAPP_SNAPSHOT_CLI`
  - Absolute path or command name for `gcapp_snapshot_cli`
- `DFM_GCAPP_WORK_DIR`
  - Optional persistent directory where dfm-engine stores generated GCAPP runs
- `DFM_GCAPP_OUTPUT_DIR`
  - Optional fallback directory containing pre-generated `model.json` and snapshots

## Fallback Behavior

The adapter uses this order:

1. If `DFM_GCAPP_OUTPUT_DIR` is set:
   - do not call the CLI tools
   - read the pre-generated artifacts directly
2. Else:
   - call `gcapp_cli`
   - call `gcapp_snapshot_cli` if it is available
3. If `gcapp_snapshot_cli` is unavailable:
   - continue parsing structure
   - return a `CADModel` without snapshot assets
4. If `gcapp_cli` is unavailable and no fallback output directory is configured:
   - fail fast with a clear runtime error

## Non-Goals

This contract does not include:

- GCAPP UI automation
- Qt window interaction
- Python STEP bindings
- geometry parsing inside `dfm-engine`
