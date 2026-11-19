"""
packages/parsers — Vector and document parsers for CAD (DXF), BIM (IFC), and blueprints (PDF).
"""

from packages.parsers.dxf import parse_dxf
from packages.parsers.ifc import parse_ifc
from packages.parsers.pdf import parse_pdf

__all__ = ["parse_dxf", "parse_ifc", "parse_pdf"]
