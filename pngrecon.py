#!/usr/bin/env python3
import sys
import struct
import zlib
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

CUSTOM_TYPE = 'maTt'


class Chunk():
    def __init__(self, chunk_type, data):
        chunk_type = bytes(chunk_type, 'utf-8')
        self._data = struct.pack('>I', len(data)) + chunk_type + data +\
            struct.pack('>I', zlib.crc32(chunk_type + data))

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


file_sig = b'\x89PNG\r\n\x1a\n'
IHDR = Chunk('IHDR', struct.pack('>IIBBBBB', 1, 1, 1, 0, 0, 0, 0))
IDAT = Chunk('IDAT', zlib.compress(struct.pack('>BB', 0, 0)))
IEND = Chunk('IEND', b'')


def log(*s):
    print(*s, file=sys.stderr)


def fail_hard(*s):
    if s:
        log(*s)
    exit(1)


def main_encode(args):
    in_data = None
    with open(args.input, 'rb') as fd:
        in_data = zlib.compress(fd.read())
    if in_data is None:
        fail_hard('Error reading in data')
    d = Chunk(CUSTOM_TYPE, in_data)
    with open(args.output, 'wb') as fd:
        fd.write(file_sig)
        fd.write(IHDR.raw_data)
        fd.write(IDAT.raw_data)
        fd.write(d.raw_data)
        fd.write(IEND.raw_data)


def main_decode(args):
    chunks = []
    with open(args.input, 'rb') as fd:
        fd.seek(len(file_sig))
        while len(fd.peek(1)) > 0:
            c = Chunk.from_byte_stream(fd)
            chunks.append(c)
    with open(args.output, 'wb') as fd:
        for c in chunks:
            if c.type == CUSTOM_TYPE:
                fd.write(zlib.decompress(c.data))


def main(args):
    assert args.encode != args.decode
    if args.encode:
        return main_encode(args)
    return main_decode(args)


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-d', '--decode', action='store_true', help='Decode input')
    parser.add_argument(
        '-e', '--encode', action='store_true', help='Encode input')
    parser.add_argument(
        '-i', '--input', type=str, default='/dev/stdin',
        help='Where to read data')
    parser.add_argument(
        '-o', '--output', type=str, default='/dev/stdout',
        help='Where to write data')
    args = parser.parse_args()
    if args.decode == args.encode:
        fail_hard('Specify one of --encode or --decode')
    main(args)
