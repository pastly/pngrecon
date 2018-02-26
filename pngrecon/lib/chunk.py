from ..util.log import log
from ..util.log import fail_hard
import struct
import zlib
from enum import Enum


def read_image_stream(stream):
    ''' Read a PNG from the given stream and return an ordered list of its
    chunks. If the stream is seekable, seek to the start of the stream.
    Otherwise assumes we're at the start of a PNG '''
    chunks = []
    if stream.seekable():
        stream.seek(0, 0)
    stream.read(len(PNG_SIG))
    while len(stream.peek(1)) > 0:
        c = Chunk.from_byte_stream(stream)
        chunks.append(c)
    return chunks


def encode_stream_as_chunks(stream):
    ''' The input stream should contain bytes that the user wishes to encode
    into a PNG. If seekable, seek to the start. Otherwise assume we are at the
    start of the data the user wishes to encode.

    Returns an ordered list of all the chunks that need to be stored in the
    image. '''
    if stream.seekable():
        stream.seek(0, 0)
    bites = []
    while len(stream.peek(1)) > 0:
        bites.append(stream.read(MAX_DATA_CHUNK_BYTES))
    index_chunk = IndexChunk(
        EncodingType.SingleFile, CompressMethod.No, len(bites))
    data_chunks = [DataChunk(CompressMethod.No, bite) for bite in bites]
    return [index_chunk] + data_chunks


def decode_chunks_to_bytes(chunks):
    ''' The input stream should contain a bunch of Chunks. All of them do not
    need to be known chunk types, but the right number and order of known
    chunk types should be present. '''
    index_chunk = None
    return_bytes = b''
    for chunk in chunks:
        # TODO: Determining if a chunk is one we care about by using exceptions
        # is ugly. It may even be uncomfortably slow. Replace with something
        # better. One idea: an lre_cache'ed function that catches exceptions
        try:
            ChunkType(chunk.type)
        except ValueError:
            continue
        chunk_type = ChunkType(chunk.type)
        if index_chunk is None and chunk_type != ChunkType.Index:
            fail_hard('Malformed: first of our chunks should be an IndexChunk')
        if index_chunk is None:
            assert chunk_type == ChunkType.Index
            index_chunk = chunk
            continue
        elif chunk_type == ChunkType.Data:
            return_bytes += chunk.data
    return return_bytes


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
        chunk_type = str(chunk_type, 'utf-8')
        chunk_data = stream.read(chunk_len)
        chunk_crc, = struct.unpack('>I', stream.read(4))
        chunk = Chunk(chunk_type, chunk_data)
        # it should be valid ... because we just calculated the crc ourselves
        assert chunk.is_valid
        # but what may not be true is that the calculated crc matches the
        # given crc
        if chunk.crc != chunk_crc:
            log('Created chunk of type', chunk.type, 'and its CRC doesn\'t '
                'match the given one.')
        return chunk

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
    def data(self):
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
        crc2 = zlib.crc32(bytes(self.type, 'utf-8') + self.data)
        return crc1 == crc2

    @property
    def raw_data(self):
        ''' the length, type, data, and crc all smooshed together like it would
        appear in a PNG file'''
        if not self.is_valid:
            log('Returning raw_bytes for Chunk that is not valid')
        return self._data


class ChunkType(Enum):
    Index = 'deQm'
    Data = 'maTt'


class EncodingType(Enum):
    SingleFile = 1


class CompressMethod(Enum):
    No = 1
    Zlib = 2


class IndexChunk(Chunk):
    def __init__(self, encoding_type, compress_method, num_data_chunks):
        assert isinstance(encoding_type, EncodingType)
        assert isinstance(compress_method, CompressMethod)
        assert num_data_chunks >= 0
        chunk_type = ChunkType.Index
        data = struct.pack(
            '>III', encoding_type.value, compress_method.value,
            num_data_chunks)
        super().__init__(chunk_type.value, data)

    @property
    def is_valid(self):
        if not super().is_valid:
            return False
        try:
            self.encoding_type
            self.compress_method
        except ValueError:
            return False
        return True

    @property
    def encoding_type(self):
        t, = struct.unpack_from('>I', self.data, 0)
        # throws ValueError if not valid
        return EncodingType(t)

    @property
    def compress_method(self):
        m, = struct.unpack_from('>I', self.data, 4)
        # throws ValueError if not valid
        return CompressMethod(m)

    @property
    def num_data_chunks(self):
        n, = struct.unpack_from('>I', self.data, 8)
        return n


class DataChunk(Chunk):
    def __init__(self, compress_method, data):
        assert isinstance(compress_method, CompressMethod)
        chunk_type = ChunkType.Data
        super().__init__(chunk_type.value, data)


MAX_DATA_CHUNK_BYTES = 1 * 1024 * 1024 * 1024  # 1 GiB
CUSTOM_TYPE = 'maTt'
PNG_SIG = b'\x89PNG\r\n\x1a\n'
IHDR = Chunk('IHDR', struct.pack('>IIBBBBB', 1, 1, 1, 0, 0, 0, 0))
IDAT = Chunk('IDAT', zlib.compress(struct.pack('>BB', 0, 0)))
IEND = Chunk('IEND', b'')
