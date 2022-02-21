from struct import *
import io

class BinaryStream:
    def __init__(self, base_stream: io.BufferedReader):
        self.base_stream = base_stream

    def ReadByte(self):
        return self.base_stream.read(1)

    def ReadBytes(self, length):
        return self.base_stream.read(length)

    def ReadChar(self) -> int:
        return self.unpack('c')

    def ReadInt8(self) -> int:
        return self.unpack('b')

    def ReadUInt8(self) -> int:
        return self.unpack('B')

    def ReadBool(self) -> bool:
        return self.unpack('?')

    def ReadInt16(self) -> int:
        return self.unpack('h', 2)

    def ReadUInt16(self) -> int:
        return self.unpack('H', 2)

    def ReadInt32(self) -> int:
        return self.unpack('i', 4)

    def ReadUInt32(self) -> int:
        return self.unpack('I', 4)

    def ReadInt64(self) -> int:
        return self.unpack('q', 8)

    def ReadUInt64(self) -> int:
        return self.unpack('Q', 8)

    def ReadSingle(self) -> float:
        return self.unpack('f', 4)

    def ReadDouble(self) -> float:
        return self.unpack('d', 8)

    def ReadString(self) -> str:
        length = self.ReadUInt16()
        #print(length)
        return self.unpack(str(length) + 's', length).decode("utf8")

    def ReadStringSingleByteLength(self) -> str:
        length = self.ReadUInt8()
        print(length)
        return self.unpack(str(length) + 's', length).decode("utf8")
    
    def Read7BitEncodedInt(self) -> int:
        more = True
        value = 0
        shift = 0
        while more:
            byte = self.ReadUInt8()
            value += (byte & 0x7f) << shift
            shift += 7
            more = (byte & 0x80) != 0
        
        return value
    
    def ReadCSharpString(self) -> str:
        length = self.Read7BitEncodedInt()
        return self.unpack(f"{length}s", length).decode("utf8")
            

    def WriteBytes(self, value):
        self.base_stream.write(value)

    def WriteChar(self, value):
        self.pack('c', value)

    def WriteBool(self, value):
        self.pack('?', value)

    def WriteInt8(self, value):
        self.pack('b', value)
    
    def WriteUInt8(self, value):
        self.pack('B', value)
    
    def WriteInt16(self, value):
        self.pack('h', value)

    def WriteUInt16(self, value):
        self.pack('H', value)

    def WriteInt32(self, value):
        self.pack('i', value)

    def WriteUInt32(self, value):
        self.pack('I', value)

    def WriteInt64(self, value):
        self.pack('q', value)

    def WriteUInt64(self, value):
        self.pack('Q', value)

    def WriteSingle(self, value):
        self.pack('f', value)

    def WriteDouble(self, value):
        self.pack('d', value)

    def WriteString(self, value):
        length = len(value)
        self.WriteUInt16(length)
        self.pack(str(length) + 's', value)

    def WriteStringSingleByteLength(self, value):
        length = len(value)
        self.WriteUInt8(length)
        self.pack(str(length) + 's', value.encode("utf-8"))

    def Write7BitEncodedInt(self, value: int):
        while value != 0:
            byte = value & 0x7F
            value >>= 7
            byte |= (value != 0) << 7
            self.WriteUInt8(byte)
    
    def WriteCSharpString(self, value: str):
        length = len(value)
        self.Write7BitEncodedInt(length)
        self.pack(f"{length}s", value.encode("utf-8"))
    
    def pack(self, fmt, data):
        return self.WriteBytes(pack(fmt, data))

    def unpack(self, fmt, length = 1):
        return unpack(fmt, self.ReadBytes(length))[0]