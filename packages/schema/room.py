from pydantic import BaseModel, Field
from enum import Enum

class Room(BaseModel):
    id: str
    name: str
    polygon: list[tuple[float, float]]