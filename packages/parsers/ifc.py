"""
packages/parsers/ifc.py — IFC parser using ifcopenshell.
Extracts BIM electrical components, spatial structure (rooms/storeys), and placements.
"""

from __future__ import annotations

import logging
from typing import Any

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit

from packages.schema import FileType, Project, Room, SourceType, Symbol, SymbolType

logger = logging.getLogger("imjan.parsers.ifc")

IFC_TYPE_MAP: dict[str, SymbolType] = {
    "IfcFlowTerminal": SymbolType.WANDCONTACTDOOS,
    "IfcElectricOutlet": SymbolType.WANDCONTACTDOOS,
    "IfcElectricSwitch": SymbolType.SCHAKELAAR,
    "IfcLightFixture": SymbolType.LICHTPUNT,
    "IfcDistributionBoard": SymbolType.VERDELER,
    "IfcElectricDistributionBoard": SymbolType.VERDELER,
    "IfcCommunicationsAppliance": SymbolType.DATAPUNT,
    "IfcAudioVisualAppliance": SymbolType.AUDIO_PUNT,
    "IfcAlarm": SymbolType.ROOKMELDER,
    "IfcSensor": SymbolType.BEWEGINGSMELDER,
    "IfcElectricMotor": SymbolType.VENTILATIEUNIT,
}


def _get_element_coords(element: Any, unit_scale: float) -> tuple[float, float, float]:
    """Extracts world/local XYZ coordinates in millimeters."""
    try:
        if hasattr(element, "ObjectPlacement") and element.ObjectPlacement:
            matrix = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
            x, y, z = matrix[0][3], matrix[1][3], matrix[2][3]
            # Convert units to mm (ifcopenshell unit_scale is meters-to-project unit)
            # unit_scale gives mm multiplier if unit is meters (scale = 1000)
            return float(x) * unit_scale, float(y) * unit_scale, float(z) * unit_scale
    except Exception as exc:
        logger.debug("Could not resolve placement for %s: %s", element, exc)
    return 0.0, 0.0, 0.0


def parse_ifc(data: bytes) -> Project:
    """
    Parses IFC file bytes and returns a populated Project model.
    """
    try:
        text = data.decode("utf-8", errors="replace")
        model = ifcopenshell.file.from_string(text)
    except Exception as exc:
        logger.error("Failed to parse IFC file: %s", exc)
        return Project(file_type=FileType.IFC, meta={"error": str(exc)})

    # Determine unit scale (multiplier to convert project units to mm)
    unit_scale = 1000.0  # Default IFC unit is typically meters -> 1000mm
    try:
        scale_val = ifcopenshell.util.unit.calculate_unit_scale(model)
        if scale_val:
            # calculate_unit_scale returns meters per unit; multiply by 1000 for mm
            unit_scale = float(scale_val) * 1000.0
    except Exception:
        unit_scale = 1000.0

    rooms: list[Room] = []
    space_id_to_room: dict[str, Room] = {}

    # Extract spaces (IfcSpace)
    try:
        spaces = model.by_type("IfcSpace")
    except RuntimeError:
        # Schema not loaded or type not found — treat as empty
        logger.warning("IFC schema not loaded properly; returning empty project")
        return Project(file_type=FileType.IFC, meta={"error": "No IFC schema loaded"})

    for space in spaces:
        space_name = getattr(space, "LongName", None) or getattr(space, "Name", None) or "Ruimte"
        sx, sy, _ = _get_element_coords(space, unit_scale)
        room = Room(
            name=str(space_name),
            polygon=[
                [sx - 2000, sy - 2000],
                [sx + 2000, sy - 2000],
                [sx + 2000, sy + 2000],
                [sx - 2000, sy + 2000],
            ],
        )
        rooms.append(room)
        space_id_to_room[str(space.GlobalId)] = room

    # Map spatial containment (which element is inside which space)
    element_to_space: dict[str, str] = {}
    try:
        for rel in model.by_type("IfcRelContainedInSpatialStructure"):
            relating_struct = rel.RelatingStructure
            if relating_struct and relating_struct.is_a("IfcSpace"):
                space_gid = str(relating_struct.GlobalId)
                for elem in rel.RelatedElements:
                    element_to_space[str(elem.GlobalId)] = space_gid
    except RuntimeError:
        logger.debug("Could not query IfcRelContainedInSpatialStructure")

    symbols: list[Symbol] = []
    for ifc_class, sym_type in IFC_TYPE_MAP.items():
        try:
            elements = model.by_type(ifc_class)
        except RuntimeError:
            continue
        for elem in elements:
            elem_gid = str(elem.GlobalId)
            x, y, _ = _get_element_coords(elem, unit_scale)

            # Assign room from BIM relationship
            room_id = None
            if elem_gid in element_to_space:
                space_gid = element_to_space[elem_gid]
                if space_gid in space_id_to_room:
                    room_id = space_id_to_room[space_gid].id

            # Extract possible circuit info from electrical ports or attributes
            circuit = None
            if hasattr(elem, "Tag") and elem.Tag:
                circuit = str(elem.Tag)

            sym = Symbol(
                type=sym_type,
                x=round(x, 2),
                y=round(y, 2),
                room_id=room_id,
                circuit=circuit,
                confidence=1.0,
                source=SourceType.VECTOR,
                attributes={
                    "ifc_type": ifc_class,
                    "global_id": elem_gid,
                    "name": getattr(elem, "Name", ""),
                },
            )
            symbols.append(sym)

    meta = {
        "parser": "ifcopenshell",
        "schema": getattr(model, "schema", "IFC"),
        "unit_scale_to_mm": unit_scale,
        "total_elements": len(symbols),
        "total_rooms": len(rooms),
    }

    return Project(
        file_type=FileType.IFC,
        scale=unit_scale,
        rooms=rooms,
        symbols=symbols,
        meta=meta,
    )
