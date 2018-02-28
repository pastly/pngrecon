from ..lib.chunk import read_image_stream
from ..lib.chunk import ChunkType
from ..util.log import log
from ..util.log import fail_hard
from argparse import ArgumentDefaultsHelpFormatter
import os


def gen_parser(sub_p):
    p = sub_p.add_parser('info', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('image', nargs='?', default='/dev/stdin')


def main(args):
    if not os.path.exists(args.image):
        fail_hard(args.image, 'must exist')
    if os.path.isdir(args.image):
        fail_hard('Image can\'t be a directory')
    with open(args.image, 'rb') as fd:
        chunks = read_image_stream(fd)
    log(args.image, 'contains', len(chunks), 'chunks')
    for c in chunks:
        try:
            chunk_type = ChunkType(c.type)
        except ValueError:
            chunk_type = None
        if chunk_type is None:
            chunk_type = 'Chunk {}'.format(c.type)
        log(chunk_type, 'with len', c.length)
