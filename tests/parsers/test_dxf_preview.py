import io

import ezdxf
import pytest

from packages.parsers.dxf import parse_dxf
from packages.parsers.dxf_preview import preview_paths


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_preview_and_parser_accept_dxf_in_millimeters(newline):
    doc = ezdxf.new(units=6)  # meters
    doc.layers.new("hidden").off()
    model = doc.modelspace()
    model.add_line((1, 2), (3, 4))
    model.add_line((0, 0), (9, 9), dxfattribs={"layer": "hidden"})
    block = doc.blocks.new("WCD")
    model.add_blockref(block.name, (2, 3))
    stream = io.StringIO()
    doc.write(stream)

    data = stream.getvalue().replace("\n", newline).encode()
    paths, truncated = preview_paths(data)
    project = parse_dxf(data)

    assert not truncated
    assert paths == [[(1000, 2000), (3000, 4000)]]
    assert [(symbol.x, symbol.y) for symbol in project.symbols] == [(2000, 3000)]
