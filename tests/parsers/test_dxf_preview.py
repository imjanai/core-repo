import io

import ezdxf

from packages.parsers.dxf_preview import preview_paths


def test_preview_uses_model_coordinates_in_millimeters():
    doc = ezdxf.new(units=6)  # meters
    doc.layers.new("hidden").off()
    model = doc.modelspace()
    model.add_line((1, 2), (3, 4))
    model.add_line((0, 0), (9, 9), dxfattribs={"layer": "hidden"})
    stream = io.StringIO()
    doc.write(stream)

    paths, truncated = preview_paths(stream.getvalue().encode())

    assert not truncated
    assert paths == [[(1000, 2000), (3000, 4000)]]
