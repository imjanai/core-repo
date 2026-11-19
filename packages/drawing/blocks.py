"""
packages/drawing/blocks.py — Standard electrical block definitions for ezdxf.
Draws vector geometries for European electrical symbols (AREI / NEN 1010).
"""

from __future__ import annotations

from typing import Callable
import ezdxf
from packages.schema import SymbolType


def _draw_socket(block) -> None:
    # Circle with 150mm radius + base ground prong
    block.add_circle((0, 0), radius=150)
    block.add_line((-150, 0), (150, 0))
    block.add_line((0, 0), (0, -150))


def _draw_double_socket(block) -> None:
    # Double socket: two intersecting semi-circles or double prongs
    block.add_circle((0, 0), radius=150)
    block.add_line((-150, 0), (150, 0))
    block.add_line((-50, 0), (-50, -150))
    block.add_line((50, 0), (50, -150))


def _draw_switch(block) -> None:
    # Circle + angled lever
    block.add_circle((0, 0), radius=100)
    block.add_line((0, 0), (120, 120))
    block.add_line((120, 120), (180, 120))


def _draw_light(block) -> None:
    # Diagonal cross (X)
    s = 150
    block.add_line((-s, -s), (s, s))
    block.add_line((-s, s), (s, -s))


def _draw_spot(block) -> None:
    # Circle with cross inside
    block.add_circle((0, 0), radius=120)
    s = 85
    block.add_line((-s, -s), (s, s))
    block.add_line((-s, s), (s, -s))


def _draw_data(block) -> None:
    # Triangle pointing up
    block.add_lwpolyline([(-120, -100), (120, -100), (0, 140), (-120, -100)], close=True)


def _draw_panel(block) -> None:
    # Rectangle with diagonal split
    w, h = 300, 500
    block.add_lwpolyline([(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)], close=True)
    block.add_line((-w/2, -h/2), (w/2, h/2))


def _draw_smoke(block) -> None:
    # Outer circle with inner letter 'R' or dot
    block.add_circle((0, 0), radius=150)
    block.add_circle((0, 0), radius=60)


SYMBOL_BUILDERS: dict[SymbolType, Callable[[Any], None]] = {
    SymbolType.WANDCONTACTDOOS: _draw_socket,
    SymbolType.WANDCONTACTDOOS_DUBBEL: _draw_double_socket,
    SymbolType.WANDCONTACTDOOS_WATERDICHT: _draw_socket,
    SymbolType.WANDCONTACTDOOS_KRACHT: _draw_socket,
    SymbolType.SCHAKELAAR: _draw_switch,
    SymbolType.SCHAKELAAR_WISSEL: _draw_switch,
    SymbolType.SCHAKELAAR_KRUIS: _draw_switch,
    SymbolType.SCHAKELAAR_DIMMER: _draw_switch,
    SymbolType.LICHTPUNT: _draw_light,
    SymbolType.LICHTPUNT_SPOT: _draw_spot,
    SymbolType.LICHTPUNT_TL: _draw_light,
    SymbolType.DATAPUNT: _draw_data,
    SymbolType.DATAPUNT_DUBBEL: _draw_data,
    SymbolType.VERDELER: _draw_panel,
    SymbolType.GROEPENKAST: _draw_panel,
    SymbolType.ROOKMELDER: _draw_smoke,
}


def register_blocks(doc) -> None:
    """Registers standard electrical blocks in the DXF drawing."""
    for st, builder in SYMBOL_BUILDERS.items():
        block_name = f"IMJAN-{st.value.upper()}"
        if block_name not in doc.blocks:
            blk = doc.blocks.new(name=block_name)
            builder(blk)
