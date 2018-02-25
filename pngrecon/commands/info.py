from ..lib.chunk import read_image_stream
from ..util.log import log
from argparse import ArgumentDefaultsHelpFormatter


def gen_parser(sub_p):
    p = sub_p.add_parser('info', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('image')


def main(args):
    with open(args.image, 'rb') as fd:
        chunks = read_image_stream(fd)
    log(args.image, 'contains', len(chunks), 'chunks')
    for c in chunks:
        log('Chunk', c.type, 'with len', c.length)
