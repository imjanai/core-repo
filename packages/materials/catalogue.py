"""
packages/materials/catalogue.py — laadt het artikelcatalogus uit catalogue.json.

De catalogus koppelt elk SymbolType aan één standaardartikel:
ETIM-code, omschrijving, eenheid en indicatieve eenheidsprijs.

Voor productie kan dit vervangen worden door een groothandel-API-client
(bijv. Sonepar, Rexel, Van Marcke) — de interface blijft hetzelfde.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict


class CatalogueEntry(TypedDict):
    symbol_type: str
    etim_code: str | None
    description: str
    unit: str
    unit_price: float | None
    brand_hint: str | None


_CATALOGUE_PATH = Path(__file__).parent / "catalogue.json"


@lru_cache(maxsize=1)
def load_catalogue() -> dict[str, CatalogueEntry]:
    """
    Laadt catalogue.json één keer en cacht het resultaat.
    Sleutel = symbol_type (string, lowercase).
    """
    with _CATALOGUE_PATH.open(encoding="utf-8") as fh:
        entries: list[CatalogueEntry] = json.load(fh)
    return {e["symbol_type"]: e for e in entries}


def get_entry(symbol_type: str) -> CatalogueEntry:
    """
    Geeft het catalogusartikel voor een symbooltype.
    Val terug op de 'onbekend'-entry als het type niet gevonden wordt.
    """
    cat = load_catalogue()
    return cat.get(symbol_type, cat["onbekend"])


def reload_catalogue() -> None:
    """Forceer herlaad van de catalogus (handig na een update in tests)."""
    load_catalogue.cache_clear()
