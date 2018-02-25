from ..lib.chunk import read_image_stream
from ..lib.chunk import CUSTOM_TYPE
from argparse import ArgumentDefaultsHelpFormatter
import zlib


def gen_parser(sub_p):
    p = sub_p.add_parser(
        'decode', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('-i', '--input', type=str, default='/dev/stdin',
                   help='Where to read data')
    p.add_argument('-o', '--output', type=str, default='/dev/stdout',
                   help='Where to write data')


def main(args):
    with open(args.input, 'rb') as fd:
        chunks = read_image_stream(fd)
    with open(args.output, 'wb') as fd:
        for c in chunks:
            if c.type == CUSTOM_TYPE:
                fd.write(zlib.decompress(c.data))
