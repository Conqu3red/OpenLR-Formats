from enum import Enum
from dataclasses import dataclass
import io
from typing import *

from ..binary import BinaryStream
from .line import *

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

    def update_features(self):
        """Enable features used by this track."""
        for line in self.lines:
            if isinstance(line, AccelerationLine) and line.multiplier != 1:
                self.features.add(Features.red_multiplier)
            elif isinstance(line, SceneryLine) and line.width != 1:
                self.features.add(Features.scenery_width)
        
        if self.songinfo is not None:
            self.features.add(Features.song_info)


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
            if "" in self.track.features:
                self.track.features.remove("")

    def get_metadata(self):
        metadata = {}
        if self.stream.base_stream.peek(1):
            magic = self.stream.ReadBytes(4)
            if magic != b"META":
                raise Exception(f"Incorrect metadata magic number {magic!r}")
            
            entries = self.stream.ReadInt16()
            for i in range(entries):
                string = self.ReadString()
                key, value = string.split("=", 1)
                metadata[key] = value
                # TODO: conversions of supported metadata value types
        
        self.track.metadata = metadata

    def read(self) -> Track:
        # Implemented based on https://github.com/Conqu3red/TRK-Docs/blob/master/The-TRK-Format.md

        # Header
        magic = self.stream.ReadBytes(4)
        if magic != b"TRK\xf2":
            raise Exception(f"Incorrect magic number {magic!r}")
        version = self.stream.ReadUInt8()

        # Features
        self.get_features()

        # SongInfo
        if Features.song_info in self.track.features:
            s = self.stream.ReadCSharpString()
            name, offset = s.split("\r\n", 1)
            self.track.songinfo = SongInfo(name, float(offset))
        
        # Line Data
        
        # Rider Position
        self.track.riderPosition.x = self.stream.ReadDouble()
        self.track.riderPosition.y = self.stream.ReadDouble()

        # Lines
        line_count = self.stream.ReadUInt32()
        for i in range(line_count):
            flags = self.stream.ReadUInt8()
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

            zoom_trigger: Optional[LineZoomTrigger] = None

            if Features.red_multiplier in self.track.features and line_type == LineType.Acceleration:
                multiplier = self.stream.ReadUInt8()
            
            if line_type == LineType.Standard or line_type == LineType.Acceleration:
                if Features.ignorable_trigger in self.track.features:
                    has_zoom_trigger = self.stream.ReadBool()
                    if has_zoom_trigger:
                        target = self.stream.ReadSingle()
                        frames = self.stream.ReadInt16()
                        zoom_trigger = LineZoomTrigger(target, frames)

                id = self.stream.ReadInt32()
                
                if extension != LineExtension.Nothing:
                    self.stream.ReadInt32() # ignored
                    self.stream.ReadInt32() # ignored
            
            if line_type == LineType.Scenery and Features.scenery_width in self.track.features:
                width = self.stream.ReadUInt8() / 10
            
            x1 = self.stream.ReadDouble()
            y1 = self.stream.ReadDouble()
            x2 = self.stream.ReadDouble()
            y2 = self.stream.ReadDouble()
            start = Vector2d(x1, y1)
            end = Vector2d(x2, y2)

            if line_type == LineType.Scenery:
                self.track.lines.append(
                    SceneryLine(start, end, width=width)
                )
            
            elif line_type == LineType.Standard:
                self.track.lines.append(
                    StandardLine(start, end, id, extension=extension, inverted=inverted, zoom_trigger=zoom_trigger)
                )
            
            elif line_type == LineType.Acceleration:
                self.track.lines.append(
                    AccelerationLine(start, end, id, extension=extension, inverted=inverted, multiplier=multiplier, zoom_trigger=zoom_trigger)
                )

        # Metadata
        self.get_metadata()

        return self.track


class TRK_Writer:
    def __init__(self, buffer: io.BufferedReader, track: Track) -> None:
        self.stream = BinaryStream(buffer)
        self.track = track
    
    def WriteString(self, string: str):
        self.stream.WriteInt16(len(string))
        self.stream.WriteBytes(string.encode("ASCII"))
    
    def write_features(self):
        self.WriteString(";".join([*self.track.features, ""]))

    def write_metadata(self):
        if self.track.metadata:
            self.stream.WriteBytes(b"META")
            self.stream.WriteInt16(len(self.track.metadata))
            
            for key, value in self.track.metadata.items():
                self.WriteString(f"{key}={value}")

    def write(self):
        self.track.update_features() # TODO: should this be here?
        
        # Header
        self.stream.WriteBytes(b"TRK\xf2")
        self.stream.WriteUInt8(1)

        # Features
        self.write_features()

        if Features.song_info in self.track.features and self.track.songinfo != None:
            self.stream.WriteCSharpString(f"{self.track.songinfo.name}\r\n{self.track.songinfo.offset}")
        
        # Line Data

        # Rider Position
        self.stream.WriteDouble(self.track.riderPosition.x)
        self.stream.WriteDouble(self.track.riderPosition.y)

        # Lines
        self.stream.WriteInt32(len(self.track.lines))

        for line in self.track.lines:
            line_type = line.type
            extension = LineExtension.Nothing
            inverted = False

            if isinstance(line, StandardLine):
                extension = line.extension
                inverted = line.inverted
            
            """
            Flag Bits:
                Bit   87654321
                Value IEETTTTT

                I: Inverted
                E: Extension
                T: Line Type
            """

            flags = (inverted << 7) + (extension.value << 5) + line_type.value
            self.stream.WriteUInt8(flags)

            if isinstance(line, AccelerationLine) and Features.red_multiplier in self.track.features:
                self.stream.WriteUInt8(line.multiplier)
            
            if isinstance(line, StandardLine):
                if Features.ignorable_trigger in self.track.features:
                    self.stream.WriteBool(line.zoom_trigger is not None)
                    if line.zoom_trigger is not None:
                        self.stream.WriteSingle(line.zoom_trigger.target_zoom)
                        self.stream.WriteInt16(line.zoom_trigger.frames)
                
                self.stream.WriteInt32(line.id)
                if line.extension != LineExtension.Nothing:
                    # Legacy data, no longer used.
                    self.stream.WriteInt32(-1)
                    self.stream.WriteInt32(-1)
                
            if isinstance(line, SceneryLine) and Features.scenery_width in self.track.features:
                self.stream.WriteUInt8(int(line.width * 10))
            
            self.stream.WriteDouble(line.start.x)
            self.stream.WriteDouble(line.start.y)
            self.stream.WriteDouble(line.end.x)
            self.stream.WriteDouble(line.end.y)
                

        # Metadata
        self.write_metadata()
