from pydantic import BaseModel, Field
from enum import Enum
from packages.schema.room import Room
from packages.schema.symbol import Symbol


class Project(BaseModel):
    id: str
    scale: float = Field(..., description="mm per tekeningeenheid")
    rooms: list[Room] = []
    symbols: list[Symbol] = []
    warnings: list[str] = []