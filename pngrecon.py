#!/usr/bin/env python3
import sys
import struct
import zlib
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from lib.chunk import Chunk
from lib.chunk import read_image_stream

CUSTOM_TYPE = 'maTt'


PNG_SIG = b'\x89PNG\r\n\x1a\n'
IHDR = Chunk('IHDR', struct.pack('>IIBBBBB', 1, 1, 1, 0, 0, 0, 0))
IDAT = Chunk('IDAT', zlib.compress(struct.pack('>BB', 0, 0)))
IEND = Chunk('IEND', b'')


def log(*s):
    print(*s, file=sys.stderr)


def fail_hard(*s):
    if s:
        log(*s)
    exit(1)


def encode_with_source_image(args, data_chunk):
    with open(args.source, 'rb') as fd:
        source_chunks = read_image_stream(fd)
    if source_chunks[-1].type != 'IEND':
        fail_hard('Don\'t know how to handle image with last chunk type',
                  source_chunks[-1].type)
    with open(args.output, 'wb') as fd:
        fd.write(PNG_SIG)
        for c in source_chunks[0:-1]:
            fd.write(c.raw_data)
        fd.write(data_chunk.raw_data)
        fd.write(source_chunks[-1].raw_data)


def main_encode(args):
    in_data = None
    with open(args.input, 'rb') as fd:
        in_data = zlib.compress(fd.read())
    if in_data is None:
        fail_hard('Error reading in data')
    d = Chunk(CUSTOM_TYPE, in_data)
    if args.source:
        return encode_with_source_image(args, d)
    with open(args.output, 'wb') as fd:
        fd.write(PNG_SIG)
        fd.write(IHDR.raw_data)
        fd.write(IDAT.raw_data)
        fd.write(d.raw_data)
        fd.write(IEND.raw_data)


def main_decode(args):
    with open(args.input, 'rb') as fd:
        chunks = read_image_stream(fd)
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
    parser.add_argument(
        '--source', type=str, default=None,
        help='When encoding, use the specified source PNG as a base instead '
        'of the tiny default base PNG')
    args = parser.parse_args()
    if args.decode == args.encode:
        fail_hard('Specify one of --encode or --decode')
    if args.decode and args.source:
        fail_hard('Specifying --source with --decode doesn\'t make sense')
    if args.source is not None and not os.path.isfile(args.source):
        fail_hard(args.source, 'must exist')
    main(args)
