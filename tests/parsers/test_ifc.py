"""
tests/parsers/test_ifc.py — Unit tests for the IFC parser.
"""

import ifcopenshell
import pytest

from packages.parsers.ifc import parse_ifc
from packages.schema import FileType, SymbolType


def test_parse_ifc_basic():
    model = ifcopenshell.file(schema="IFC4")
    # Add minimal required project structure
    project = model.create_entity("IfcProject", GlobalId=ifcopenshell.guid.new(), Name="Test Project")
    # IFC4 requires a context for valid files
    ctx = model.create_entity(
        "IfcGeometricRepresentationContext",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
    )
    units = model.create_entity("IfcUnitAssignment", Units=[])
    project.UnitsInContext = units
    project.RepresentationContexts = [ctx]

    space = model.create_entity("IfcSpace", GlobalId=ifcopenshell.guid.new(), Name="Keuken")
    # IfcFlowTerminal is a valid IFC4 entity that covers electrical outlets
    outlet = model.create_entity("IfcFlowTerminal", GlobalId=ifcopenshell.guid.new(), Name="Stopcontact 1")

    # Connect outlet to space
    rel = model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=ifcopenshell.guid.new(),
        RelatingStructure=space,
        RelatedElements=[outlet],
    )

    ifc_bytes = model.to_string().encode("utf-8")
    parsed = parse_ifc(ifc_bytes)

    assert parsed.file_type == FileType.IFC
    assert len(parsed.rooms) == 1
    assert parsed.rooms[0].name == "Keuken"
    # IfcFlowTerminal is mapped in the parser
    assert len(parsed.symbols) >= 1


def test_parse_ifc_invalid_bytes():
    parsed = parse_ifc(b"GARBAGE BYTES")
    assert parsed.file_type == FileType.IFC
