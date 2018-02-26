from ..lib.chunk import read_image_stream
from ..lib.chunk import ChunkType
from ..util.log import log
from argparse import ArgumentDefaultsHelpFormatter


def gen_parser(sub_p):
    p = sub_p.add_parser('info', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('image', nargs='?', default='/dev/stdin')


def main(args):
    with open(args.image, 'rb') as fd:
        chunks = read_image_stream(fd)
    log(args.image, 'contains', len(chunks), 'chunks')
    for c in chunks:
        try:
            chunk_type = ChunkType(c.type)
        except ValueError:
            chunk_type = None
        if chunk_type is not None:
            if chunk_type == ChunkType.Index:
                chunk_type = 'IndexChunk'
            elif chunk_type == ChunkType.Data:
                chunk_type = 'DataChunk'
            else:
                chunk_type = 'Chunk {} (pngrecon???)'.format(c.type)
        else:
            chunk_type = 'Chunk {}'.format(c.type)
        log(chunk_type, 'with len', c.length)
