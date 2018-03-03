from ..lib.chunk import read_image_stream
from ..lib.chunk import ChunkType
from ..lib.chunk import (IndexChunk, DataChunk, CryptInfoChunk)
from ..util.log import log_stdout as log
from ..util.log import fail_hard
from argparse import ArgumentDefaultsHelpFormatter
import os


def gen_parser(sub_p):
    p = sub_p.add_parser('info', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('image', nargs='*', default='/dev/stdin')


def get_chunk_extra_info_index(chunk):
    assert isinstance(chunk, IndexChunk)
    encoding_type = chunk.encoding_type
    encryption_type = chunk.encryption_type
    compress_method = chunk.compress_method
    num_data_chunks = 'Claming {} data chunks'.format(chunk.num_data_chunks)
    return [encoding_type, encryption_type, compress_method, num_data_chunks]


def get_chunk_extra_info_data(chunk):
    assert isinstance(chunk, DataChunk)
    index = 'Index {}'.format(chunk.index)
    payload = '{} bytes of data'.format(len(chunk.data))
    return [index, payload]


def get_chunk_extra_info_crypt_info(chunk):
    assert isinstance(chunk, CryptInfoChunk)
    return []


def get_chunk_extra_info(chunk):
    ''' if chunk is one of our chunks and we have extra info to log about it,
    return a list of strings that should be printed to the user containing the
    extra info '''
    if isinstance(chunk, IndexChunk):
        return get_chunk_extra_info_index(chunk)
    elif isinstance(chunk, DataChunk):
        return get_chunk_extra_info_data(chunk)
    elif isinstance(chunk, CryptInfoChunk):
        return get_chunk_extra_info_crypt_info(chunk)
    else:
        return []


def main(args):
    if not isinstance(args.image, list):
        args.image = [args.image]
    for image in args.image:
        if not os.path.exists(image):
            log(image, 'doesn\'t exist, so skipping.')
            continue
        if os.path.isdir(image):
            log(image, 'is a directory, so skipping.')
            continue
        with open(image, 'rb') as fd:
            chunks = read_image_stream(fd)
        if chunks is None:
            fail_hard(image, 'does not appear to be a PNG')
        log(image, 'contains', len(chunks), 'chunks')
        for c in chunks:
            try:
                chunk_type = ChunkType(c.type)
                if chunk_type == ChunkType.Index:
                    c = IndexChunk.from_chunk(c)
                elif chunk_type == ChunkType.CryptInfo:
                    c = CryptInfoChunk.from_chunk(c)
                elif chunk_type == ChunkType.Data:
                    c = DataChunk.from_chunk(c)
            except ValueError:
                chunk_type = None
            if chunk_type is None:
                chunk_type = 'Chunk {}'.format(c.type)
            valid = '' if c.is_valid else '(INVALID)'
            log(chunk_type, 'with len', c.length, valid)
            for line in get_chunk_extra_info(c):
                log('   ', line)
