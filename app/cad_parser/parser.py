from typing import Optional

from app.cad_parser.factory import get_cad_parser
from app.models.schemas import CADModel


def parse_step_file(
    step_filename: str,
    step_bytes: Optional[bytes] = None,
    parser_type: Optional[str] = None,
) -> CADModel:
    """Facade kept for the current workflow.

    Today this routes to the mock parser. A future real parser only needs to
    implement the CADParser interface and be selected via `parser_type`.
    """

    parser = get_cad_parser(parser_type=parser_type)
    return parser.parse(step_filename=step_filename, step_bytes=step_bytes)
