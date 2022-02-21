from enum import Enum, IntEnum
from dataclasses import dataclass, field
import io
from typing import *

from ..binary import BinaryStream


@dataclass
class Vector2d:
    x: float
    y: float


class LineExtension(IntEnum):
    Nothing = 0
    Left = 1
    Right = 2
    Both = 3


@dataclass
class PhysicsLine:
    id: int
    start: Vector2d
    end: Vector2d
    type: int # TODO: enum
    flipped: bool = False
    extension: LineExtension = LineExtension.Nothing


@dataclass
class SceneryLine:
    id: int
    start: Vector2d
    end: Vector2d

@dataclass
class Rider:
    position: Vector2d

@dataclass
class VersionInfo:
    in_development: bool = False
    engine_version: int = 0
    library_version: int = 0
    save_revision: int = 1
    source_port_version: int = 0

@dataclass
class Track:
    name: str
    author: str
    grid_model: int
    version_info: VersionInfo
    physics_lines: List[PhysicsLine]
    scenery_lines: List[SceneryLine]
    riders: List[Rider]

@dataclass
class Lump:
    type: str
    position: int


class LRPK_Reader:
    def __init__(self, buffer: io.BufferedReader) -> None:
        self.HEADER_SIZE = 0
        self.stream = BinaryStream(buffer)
        self.track = Track("", "", 0, VersionInfo(), [], [], [])
        self.lump_lookup = {
            "VERSINFO": self.read_versinfo,
            "TRACKDEF": self.read_trackdef,
            "LINEDEF": self.read_linedef,
            "LINEDECO": self.read_linedeco,
            "RIDERDEF": self.read_riderdef,
        }
    
    def read_versinfo(self):
        self.track.version_info.in_development = self.stream.ReadBool()
        self.track.version_info.engine_version = self.stream.ReadUInt8()
        self.track.version_info.library_version = self.stream.ReadUInt8()
        self.track.version_info.save_revision = self.stream.ReadUInt8()
        self.track.version_info.source_port_version = self.stream.ReadUInt8()

    
    def read_trackdef(self):
        self.track.name = self.stream.ReadBytes(self.stream.ReadUInt8()).decode("utf8")
        self.track.author = self.stream.ReadBytes(self.stream.ReadUInt8()).decode("utf8")
        self.track.grid_model = self.stream.ReadUInt8()
    
    def read_linedef(self):
        num_lines = self.stream.ReadUInt32()
        for i in range(num_lines):
            self.track.physics_lines.append(
                PhysicsLine(
                    self.stream.ReadUInt32(),
                    Vector2d(self.stream.ReadDouble(), self.stream.ReadDouble()),
                    Vector2d(self.stream.ReadDouble(), self.stream.ReadDouble()),
                    self.stream.ReadUInt8(),
                    self.stream.ReadBool(),
                    LineExtension(self.stream.ReadUInt8())
                )
            )
    
    def read_linedeco(self):
        num_lines = self.stream.ReadUInt32()
        for i in range(num_lines):
            self.track.scenery_lines.append(
                SceneryLine(
                    self.stream.ReadUInt32(),
                    Vector2d(self.stream.ReadSingle(), self.stream.ReadSingle()),
                    Vector2d(self.stream.ReadSingle(), self.stream.ReadSingle()),
                )
            )
    
    def read_riderdef(self):
        self.track.riders.append(
            Rider(Vector2d(self.stream.ReadDouble(), self.stream.ReadDouble()))
        )

    def read_directories(self):
        lump_count = self.stream.ReadUInt32()
        directory_pointer = self.stream.ReadUInt32()

        self.HEADER_SIZE = self.stream.base_stream.tell() + 1

        self.stream.base_stream.seek(directory_pointer)

        for i in range(lump_count):
            lump = Lump(
                type=self.stream.ReadBytes(8).decode("utf8").strip(),
                position=self.stream.ReadUInt32()
            )

            if i == 0:
                assert lump.type == "VERSINFO", "Expected Version info as first lump"

            print(f"lump {lump.type!r} at {lump.position}")
            if lump.type in self.lump_lookup:
                pos = self.stream.base_stream.tell()
                self.stream.base_stream.seek(lump.position) # + HEADER_SIZE?
                
                self.lump_lookup[lump.type]()
                
                self.stream.base_stream.seek(pos)
            
            else:
                raise Exception(f"Unsupported Lump {lump.type!r}")
                # TODO: not crash
    
    def read(self) -> Track:
        # Implementation of https://github.com/kevansevans/OpenLR/wiki/The-LRPK-Format

        # Header
        magic = self.stream.ReadBytes(4)
        if magic != b"LRPK":
            raise Exception(f"Incorrect magic number {magic!r}")

        # Directories
        self.read_directories()

        return self.track

class LRPK_Writer:
    def __init__(self, buffer: io.BufferedReader, track: Track) -> None:
        self.stream = BinaryStream(buffer)
        self.track = track
    
    # TODO: Writer
