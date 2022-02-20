from enum import Enum
from dataclasses import dataclass
import io
from typing import *

from binary import BinaryStream
from line import *

class Features:
    red_multiplier = "REDMULTIPLIER"
    scenery_width = "SCENERYWIDTH"
    six_one = "SIX_ONE"
    song_info = "SONGINFO"
    ignorable_trigger = "IGNORABLE_TRIGGER"
    zerostart = "ZEROSTART"
    # LRA-CE:
    remount = "REMOUNT"
    frictionless = "FRICTIONLESS"

@dataclass
class SongInfo:
    name: str
    offset: float

@dataclass
class Track:
    lines: List[BaseLine]
    features: Set[str]
    songinfo: Optional[SongInfo]
    metadata: Optional[Dict[str, str]]
    riderPosition: Vector2d

class TRK_Reader:
    def __init__(self, buffer: io.BufferedReader) -> None:
        self.stream = BinaryStream(buffer)
        self.track = Track([], set(), None, None, Vector2d(0, 0))

    
    def ReadString(self):
        return self.stream.ReadBytes(self.stream.ReadInt16()).decode("ASCII")

    def get_features(self):
        string = self.ReadString()
        if string:
            self.track.features = set(string.split(";"))

    def get_metadata(self):
        metadata = {}
        if self.stream.base_stream.peek():
            magic = self.stream.ReadBytes(4)
            if magic != b"META":
                raise Exception(f"Incorrect metadata magic number {magic!r}")
            
            entries = self.stream.ReadInt16()
            for i in range(entries):
                string = self.ReadString()
                key, value = string.split("=")
                metadata[key] = value
                # TODO: conversions of supported metadata value types

    def read(self) -> Track:
        # Implemented based on https://github.com/Conqu3red/TRK-Docs/blob/master/The-TRK-Format.md

        # Header
        magic = self.stream.ReadBytes(4)
        if magic != b"TRK\xf2":
            raise Exception(f"Incorrect magic number {magic!r}")
        version = self.stream.ReadUChar()

        # Features
        self.get_features()

        # SongInfo
        if Features.song_info in self.track.features:
            s = self.stream.ReadCSharpString()
            name, offset = s.split("\r\n")
            self.track.songinfo = SongInfo(name, float(offset))
        
        # Line Data
        
        # Rider Position
        self.track.riderPosition.x = self.stream.ReadDouble()
        self.track.riderPosition.y = self.stream.ReadDouble()

        # Lines
        line_count = self.stream.ReadUInt32()
        for i in range(line_count):
            flags = self.stream.ReadUChar()
            """
            Flag Bits:
                Bit   87654321
                Value IEETTTTT

                I: Inverted
                E: Extension
                T: Line Type
            """
            inverted = (flags & 0x80) != 0
            extension = LineExtension((flags >> 5) & 0x3)
            line_type = LineType(flags & 0x1f)

            multiplier = 1
            width = 1.0
            id = -1

            if Features.red_multiplier in self.track.features and line_type == LineType.Acceleration:
                multiplier = self.stream.ReadUChar()
            
            if line_type == LineType.Standard or line_type == LineType.Acceleration:
                if Features.ignorable_trigger in self.track.features:
                    zoom_trigger = self.stream.ReadBool()
                    if zoom_trigger:
                        target = self.stream.ReadSingle()
                        frames = self.stream.ReadInt16()
                        # TODO: store

                id = self.stream.ReadInt32()
                
                if extension != LineExtension.Nothing:
                    self.stream.ReadInt32() # ignored
                    self.stream.ReadInt32() # ignored
            
            if line_type == LineType.Scenery and Features.scenery_width in self.track.features:
                width = self.stream.ReadUChar() / 10
            
            x1 = self.stream.ReadDouble()
            y1 = self.stream.ReadDouble()
            x2 = self.stream.ReadDouble()
            y2 = self.stream.ReadDouble()
            start = Vector2d(x1, y1)
            end = Vector2d(x2, y2)

            if line_type == LineType.Scenery:
                self.track.lines.append(
                    SceneryLine(start, end, width=1)
                )
            
            elif line_type == LineType.Standard:
                self.track.lines.append(
                    StandardLine(start, end, id, extension=extension, inverted=inverted)
                )
            
            elif line_type == LineType.Acceleration:
                self.track.lines.append(
                    AccelerationLine(start, end, id, extension=extension, inverted=inverted, multiplier=multiplier)
                )

        # Metadata
        self.get_metadata()

        return self.track