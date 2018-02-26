from ..lib.chunk import Chunk
from ..lib.chunk import read_image_stream
from ..lib.chunk import (CUSTOM_TYPE, PNG_SIG, IHDR, IDAT, IEND)
from ..util.log import fail_hard
from argparse import ArgumentDefaultsHelpFormatter
import os
import zlib


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


def gen_parser(sub_p):
    p = sub_p.add_parser(
        'encode', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('-i', '--input', type=str, default='/dev/stdin',
                   help='Where to read data')
    p.add_argument('-o', '--output', type=str, default='/dev/stdout',
                   help='Where to write data')
    p.add_argument(
        '-s', '--source', type=str, default=None,
        help='Use the specified source PNG as a base instead of the tiny '
        'default base PNG')


def main(args):
    if args.source is not None and not os.path.isfile(args.source):
        fail_hard(args.source, 'must exist')
    with open(args.input, 'rb') as fd:
        in_data = zlib.compress(fd.read())
    d = Chunk(CUSTOM_TYPE, in_data)
    if args.source:
        return encode_with_source_image(args, d)
    with open(args.output, 'wb') as fd:
        fd.write(PNG_SIG)
        fd.write(IHDR.raw_data)
        fd.write(IDAT.raw_data)
        fd.write(d.raw_data)
        fd.write(IEND.raw_data)
