import io
import math

import ezdxf
from ezdxf import disassemble
from ezdxf.path import make_path

from packages.parsers.dxf import INSUNITS_SCALE_TO_MM, _decode_dxf_bytes

_PATH_TYPES = {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE", "HATCH"}
_MAX_POINTS = 150_000


def preview_paths(data: bytes) -> tuple[list[list[tuple[float, float]]], bool]:
    doc = ezdxf.read(io.StringIO(_decode_dxf_bytes(data)))
    scale = INSUNITS_SCALE_TO_MM.get(int(doc.header.get("$INSUNITS", 4)), 1.0)
    hidden = {layer.dxf.name.casefold() for layer in doc.layers if layer.is_off() or layer.is_frozen()}
    visible = (entity for entity in doc.modelspace() if entity.dxf.layer.casefold() not in hidden)
    paths = []
    point_count = 0
    for entity in disassemble.recursive_decompose(visible):
        if entity.dxftype() not in _PATH_TYPES or entity.dxf.layer.casefold() in hidden:
            continue
        path = make_path(entity)
        for subpath in path.sub_paths():
            points = []
            for point in subpath.flattening(distance=2 / scale, segments=4):
                x, y = point.x * scale, point.y * scale
                if math.isfinite(x) and math.isfinite(y):
                    points.append((round(x, 2), round(y, 2)))
                    point_count += 1
                    if point_count >= _MAX_POINTS:
                        return paths, True
            if len(points) > 1:
                paths.append(points)
    return paths, False
