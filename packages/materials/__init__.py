"""
packages/materials — materiaalengine voor het elektro-ai platform.

Publieke API:
    from packages.materials import compute_materials

    project = compute_materials(project)
    # project.materials is nu gevuld met MaterialLine-objecten

Optioneel catalogusbeheer:
    from packages.materials import get_entry, reload_catalogue
"""

from packages.materials.engine import compute_materials
from packages.materials.catalogue import get_entry, reload_catalogue

__all__ = ["compute_materials", "get_entry", "reload_catalogue"]
