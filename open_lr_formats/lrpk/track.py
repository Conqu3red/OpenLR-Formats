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
        print(f"Directories at {directory_pointer}")

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
        self.directories: List[Tuple[str, int]] = []
    
    def write_versinfo(self):
        self.directories.append(("VERSINFO", self.stream.base_stream.tell()))
        self.stream.WriteBool(self.track.version_info.in_development)
        self.stream.WriteUInt8(self.track.version_info.engine_version)
        self.stream.WriteUInt8(self.track.version_info.library_version)
        self.stream.WriteUInt8(self.track.version_info.save_revision)
        self.stream.WriteUInt8(self.track.version_info.source_port_version)
    
    def write_trackdef(self):
        self.directories.append(("TRACKDEF", self.stream.base_stream.tell()))
        self.stream.WriteStringSingleByteLength(self.track.name)
        self.stream.WriteStringSingleByteLength(self.track.author)
        self.stream.WriteUInt8(self.track.grid_model)
    
    def write_linedef(self):
        self.directories.append(("LINEDEF", self.stream.base_stream.tell()))
        self.stream.WriteUInt32(len(self.track.physics_lines))
        for line in self.track.physics_lines:
            self.stream.WriteUInt32(line.id)
            self.stream.WriteDouble(line.start.x)
            self.stream.WriteDouble(line.start.y)
            self.stream.WriteDouble(line.end.x)
            self.stream.WriteDouble(line.end.y)
            self.stream.WriteUInt8(line.type)
            self.stream.WriteBool(line.flipped)
            self.stream.WriteUInt8(line.extension)  
    
    def write_linedeco(self):
        num_lines = len(self.track.scenery_lines)
        if num_lines == 0:
            return
        self.directories.append(("LINEDECO", self.stream.base_stream.tell()))
        self.stream.WriteUInt32(num_lines)
        for line in self.track.scenery_lines:
            self.stream.WriteUInt32(line.id)
            self.stream.WriteSingle(line.start.x)
            self.stream.WriteSingle(line.start.y)
            self.stream.WriteSingle(line.end.x)
            self.stream.WriteSingle(line.end.y)
    
    def write_riderdefs(self):
        for rider in self.track.riders:
            self.directories.append(("RIDERDEF", self.stream.base_stream.tell()))
            self.stream.WriteDouble(rider.position.x)
            self.stream.WriteDouble(rider.position.y)
    
    def write_directories(self):
        for name, pointer in self.directories:
            self.stream.WriteBytes(name.ljust(8).encode("ascii"))
            self.stream.WriteUInt32(pointer)
    
    def write(self):
        # Header
        self.stream.WriteBytes(b"LRPK")
        
        pointer_loc = self.stream.base_stream.tell()
        self.stream.WriteUInt32(0) # directory count
        self.stream.WriteUInt32(0) # directory pointer

        self.write_versinfo()
        self.write_linedef()
        self.write_linedeco()
        self.write_riderdefs()
        self.write_trackdef()

        directory_pointer = self.stream.base_stream.tell()
        self.write_directories()
        
        self.stream.base_stream.seek(pointer_loc)
        self.stream.WriteUInt32(len(self.directories))
        self.stream.WriteUInt32(directory_pointer)
