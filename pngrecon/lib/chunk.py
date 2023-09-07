from ..util.log import log_stderr as log
from ..util.log import fail_hard
import struct
import zlib
from enum import Enum
from functools import lru_cache


def read_image_stream(stream):
    ''' Read a PNG from the given stream and return an ordered list of its
    chunks. If the stream is seekable, seek to the start of the stream.
    Otherwise assumes we're at the start of a PNG. If the stream does not look
    like it is most likely a PNG, return None. '''
    chunks = []
    if stream.seekable():
        stream.seek(0, 0)
    if stream.read(len(PNG_SIG)) != PNG_SIG:
            log('Could not find PNG file signature')
            return None
    while len(stream.peek(1)) > 0:
        c = Chunk.from_byte_stream(stream)
        chunks.append(c)
    return chunks


class Chunk():
    def __init__(self, chunk_type, data):
        chunk_type = bytes(chunk_type, 'utf-8')
        self._data = struct.pack('>I', len(data)) + chunk_type + data +\
            struct.pack('>I', zlib.crc32(chunk_type + data))
        assert self.is_valid

    @classmethod
    def from_byte_stream(cls, stream):
        ''' If you have some bytes that are supposed to represent a Chunk
        (with its headers and everything), use this function to create a Chunk
        instance. '''
        chunk_len, = struct.unpack('>I', stream.read(4))
        chunk_type, = struct.unpack('>4s', stream.read(4))
        chunk_type_str = str(chunk_type, 'utf-8')
        chunk_type = ChunkType.from_string(chunk_type_str)
        chunk_data = stream.read(chunk_len)
        chunk_crc, = struct.unpack('>I', stream.read(4))
        chunk = Chunk(chunk_type_str, chunk_data)
        if chunk_type is None:
            pass
        elif chunk_type == ChunkType.Index:
            chunk = IndexChunk.from_chunk(chunk)
        elif chunk_type == ChunkType.CryptInfo:
            chunk = CryptInfoChunk.from_chunk(chunk)
        elif chunk_type == ChunkType.Data:
            chunk = DataChunk.from_chunk(chunk)
        else:
            fail_hard('Can\'t parse chunk', chunk_type, 'from byte stream')
        # it should be valid ... because we just calculated the crc ourselves
        assert chunk.is_valid
        # but what may not be true is that the calculated crc matches the
        # given crc
        if chunk.crc != chunk_crc:
            log('Created chunk of type', chunk.type, 'and its CRC doesn\'t '
                'match the given one.')
        return chunk

    @classmethod
    def from_chunk(cls, chunk):
        fail_hard('Not implemented for class', cls.__name__)

    @property
    def length(self):
        ''' 4-byte uint for number of bytes in data field '''
        l, = struct.unpack_from('>I', self._data, 0)
        return l

    @property
    def type(self):
        ''' 4-byte string naming the chunk type '''
        t, = struct.unpack_from('>4s', self._data, 4)
        return str(t, 'utf-8')

    @property
    def chunk_payload(self):
        ''' payload data in this chunk '''
        return self._data[8:8+self.length]

    @property
    def crc(self):
        ''' 4-byte uint crc calculated on type and data (not length) '''
        r = self._data[8+self.length:]
        assert len(r) == 4
        r, = struct.unpack('>I', r)
        return r

    @property
    def is_valid(self):
        ''' calculates the crc and checks that it matches the crc that we were
        given '''
        crc1 = self.crc
        crc2 = zlib.crc32(bytes(self.type, 'utf-8') + self.chunk_payload)
        return crc1 == crc2

    @property
    def raw_data(self):
        ''' the length, type, chunk_payload, and crc all smooshed together like
        it would appear in a PNG file'''
        if not self.is_valid:
            log('Returning raw_bytes for Chunk that is not valid')
        return self._data


# Chunk names should be <lower><lower><upper><lower>
# https://www.w3.org/TR/PNG/#table52
# lower 1st: not critical for display
# lower 2nd: private/non-standard
# upper 3rd: reservered and must be upper
# lower 4th: safe to copy
class ChunkType(Enum):
    Index = 'deQm'
    Data = 'maTt'
    CryptInfo = 'yyBo'

    @lru_cache(maxsize=8)
    def from_string(s):
        ''' Given a string, return the chunk type enum for it. Return None if
        it doesn't exist '''
        assert isinstance(s, str)
        try:
            t = ChunkType(s)
        except ValueError:
            return None
        return t


class EncodingType(Enum):
    SingleFile = 1


class EncryptionType(Enum):
    No = 1
    SaltedPass01 = 2


class CompressMethod(Enum):
    No = 1
    Zlib = 2
    Lzma = 3


class IndexChunk(Chunk):
    def __init__(self, encoding_type, encryption_type, compress_method,
                 num_data_chunks):
        assert isinstance(encoding_type, EncodingType)
        assert isinstance(encryption_type, EncryptionType)
        assert isinstance(compress_method, CompressMethod)
        assert num_data_chunks >= 0
        chunk_type = ChunkType.Index
        data = struct.pack(
            '>IIII', encoding_type.value, encryption_type.value,
            compress_method.value, num_data_chunks)
        super().__init__(chunk_type.value, data)

    @classmethod
    def from_chunk(cls, chunk):
        assert isinstance(chunk, Chunk)
        encoding_type, encryption_type, compress_method, num_data_chunks = \
            struct.unpack('>IIII', chunk.chunk_payload)
        encoding_type = EncodingType(encoding_type)
        encryption_type = EncryptionType(encryption_type)
        compress_method = CompressMethod(compress_method)
        c = IndexChunk(encoding_type, encryption_type, compress_method,
                       num_data_chunks)
        return c

    @property
    def is_valid(self):
        if not super().is_valid:
            return False
        try:
            self.encoding_type
            self.encryption_type
            self.compress_method
        except ValueError:
            return False
        if self.num_data_chunks < 0:
            return False
        return True

    @property
    def encoding_type(self):
        t, = struct.unpack_from('>I', self.chunk_payload, 0)
        # throws ValueError if not valid
        return EncodingType(t)

    @property
    def encryption_type(self):
        t, = struct.unpack_from('>I', self.chunk_payload, 4)
        # throws ValueError if not valid
        return EncryptionType(t)

    @property
    def compress_method(self):
        m, = struct.unpack_from('>I', self.chunk_payload, 8)
        # throws ValueError if not valid
        return CompressMethod(m)

    @property
    def num_data_chunks(self):
        n, = struct.unpack_from('>I', self.chunk_payload, 12)
        return n


class DataChunk(Chunk):
    def __init__(self, index, data):
        assert isinstance(index, int)
        assert index >= 0
        assert isinstance(data, bytes)
        chunk_type = ChunkType.Data
        data_len = len(data)
        d = struct.pack('>I{}s'.format(data_len), index, data)
        super().__init__(chunk_type.value, d)

    @classmethod
    def from_chunk(cls, chunk):
        assert isinstance(chunk, Chunk)
        index, = struct.unpack_from('>I', chunk.chunk_payload, 0)
        data = chunk.chunk_payload[4:]
        c = DataChunk(index, data)
        return c

    @property
    def index(self):
        i, = struct.unpack_from('>I', self.chunk_payload, 0)
        return i

    @property
    def data(self):
        return self.chunk_payload[4:]

    @property
    def is_valid(self):
        if not super().is_valid:
            return False
        return len(self.data) > 0


class CryptInfoChunk(Chunk):
    def __init__(self, salt):
        assert isinstance(salt, bytes)
        assert len(salt) == 16
        chunk_type = ChunkType.CryptInfo
        data = struct.pack('>16s', salt)
        super().__init__(chunk_type.value, data)

    @classmethod
    def from_chunk(cls, chunk):
        assert isinstance(chunk, Chunk)
        s, = struct.unpack('>16s', chunk.chunk_payload)
        c = CryptInfoChunk(s)
        return c

    @property
    def salt(self):
        s, = struct.unpack_from('>16s', self.chunk_payload, 0)
        return s

    @property
    def is_valid(self):
        if not super().is_valid:
            return False
        return self.length == 16


# The rough maximum internal buffer size to use during encoding, which will
# consequently impact the maximum chunk size in the .png. If the data to encode
# is highly compressible, this will get wonky.
#
# The max size of a chunk in the PNG spec is "like" 4 GiB (based on the chunk
# length field in chunk headers being a 32-bit uint), so do not approach this
# value. Also, smaller chunks means fun serialization problems to solve :)
TARGET_MAX_BUFFER_BYTES = 100 * 1024 * 1024  # 100 MiB
PNG_SIG = b'\x89PNG\r\n\x1a\n'
