import os
from typing import Optional

from app.cad_parser.base import CADParser
from app.cad_parser.mock_parser import MockCADParser
from app.cad_parser.real_parser import FutureRealCADParser


def get_cad_parser(parser_type: Optional[str] = None) -> CADParser:
    """Resolve the parser implementation used by the workflow.

    `mock` is the default for demo stability. When a production parser is
    available, set `parser_type="real"` or the `DFM_CAD_PARSER` env var.
    """

    resolved_type = (parser_type or os.getenv("DFM_CAD_PARSER", "mock")).strip().lower()

    if resolved_type == "mock":
        return MockCADParser()
    if resolved_type == "real":
        return FutureRealCADParser()
    raise ValueError("Unsupported CAD parser type: {0}".format(resolved_type))
