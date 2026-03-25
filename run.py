import argparse
import sys
from pathlib import Path

from app.core.workflow import WorkflowBlockingError, run_generation_from_bom_source, run_sample_generation


def main() -> int:
    parser = argparse.ArgumentParser(description="DFM Auto Generator MVP runner")
    subparsers = parser.add_subparsers(dest="command")

    sample_parser = subparsers.add_parser("sample", help="Generate the bundled sample DFM deck")
    sample_parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where the generated PPTX will be written",
    )
    sample_parser.add_argument(
        "--parser",
        default="mock",
        choices=["mock", "real"],
        help="CAD parser backend to use",
    )
    sample_parser.add_argument(
        "--bom-profile",
        default="",
        help="Optional BOM profile name. If omitted, the system auto-detects and falls back to generic.",
    )

    generate_parser = subparsers.add_parser("generate", help="Generate a deck from local STEP and BOM files")
    generate_parser.add_argument("--step-file", required=True, help="Path to the STEP input file")
    generate_parser.add_argument("--bom-file", required=True, help="Path to the BOM input file (.json or .csv)")
    generate_parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where the generated PPTX will be written",
    )
    generate_parser.add_argument(
        "--parser",
        default="mock",
        choices=["mock", "real"],
        help="CAD parser backend to use",
    )
    generate_parser.add_argument(
        "--bom-profile",
        default="",
        help="Optional BOM profile name. If omitted, the system auto-detects and falls back to generic.",
    )

    args = parser.parse_args()

    try:
        if args.command == "sample":
            result = run_sample_generation(
                output_dir=args.output_dir,
                parser_type=args.parser,
                bom_profile=args.bom_profile or None,
            )
            print(result.ppt_path)
            return 0

        if args.command == "generate":
            step_path = Path(args.step_file)
            bom_path = Path(args.bom_file)
            result = run_generation_from_bom_source(
                step_filename=step_path.name,
                step_bytes=step_path.read_bytes(),
                bom_source_name=bom_path.name,
                bom_source_bytes=bom_path.read_bytes(),
                output_dir=args.output_dir,
                parser_type=args.parser,
                bom_profile=args.bom_profile or None,
            )
            print(result.ppt_path)
            return 0
    except WorkflowBlockingError as exc:
        print(str(exc), file=sys.stderr)
        print("report_data_path={0}".format(exc.report_data_path), file=sys.stderr)
        print("selected_bom_profile={0}".format(exc.selected_bom_profile), file=sys.stderr)
        print("detected_bom_profile={0}".format(exc.detected_bom_profile), file=sys.stderr)
        for error in exc.blocking_errors:
            print("blocking_error: {0}".format(error), file=sys.stderr)
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
