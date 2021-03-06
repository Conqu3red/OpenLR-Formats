from dataclasses import dataclass, field
from typing import *
from enum import Enum

@dataclass
class Vector2d:
    x: float
    y: float

class LineType(Enum):
    Scenery = 0 # Green
    Standard = 1 # Blue
    Acceleration = 2 # Red

class LineExtension(Enum):
    Nothing = 0
    Left = 1
    Right = 2
    Both = 3

@dataclass
class BaseLine:
    start: Vector2d
    end: Vector2d

    type: ClassVar[LineType]

@dataclass
class LineZoomTrigger:
    target_zoom: float
    frames: int

@dataclass
class StandardLine(BaseLine):
    id: int
    extension: LineExtension = LineExtension.Nothing
    inverted: bool = False
    zoom_trigger: Optional[LineZoomTrigger] = None

    type = LineType.Standard

@dataclass
class AccelerationLine(StandardLine):
    multiplier: int = 1

    type = LineType.Acceleration

@dataclass
class SceneryLine(BaseLine):
    width: float = 1

    type = LineType.Scenery