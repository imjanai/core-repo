from pydantic import BaseModel, Field
from enum import Enum

class SymbolType(str, Enum):
    WCD = "wandcontactdoos"
    SWITCH = "schakelaar"
    LIGHT = "lichtpunt"
    DATA = "datapunt"
    PANEL = "verdeler"


class Symbol(BaseModel):
    id: str
    type: SymbolType
    x: float                    # in mm, op tekening
    y: float
    room_id: str | None = None
    circuit: str | None = None  # bv. "G3"
    confidence: float = 1.0
    source: str = "vector"      # vector | detector | vlm | human