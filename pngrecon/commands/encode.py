from ..lib.chunk import read_image_stream
from ..lib.chunk import (CompressMethod, EncodingType, EncryptionType)
from ..lib.chunk import (PNG_SIG, MAX_DATA_CHUNK_BYTES)
from ..lib.chunk import (Chunk, IndexChunk, DataChunk, CryptInfoChunk)
from ..util.log import fail_hard
from ..util.crypto import gen_key
from ..util.crypto import encrypt
from argparse import ArgumentDefaultsHelpFormatter
import os
import struct
import zlib


def encode_source_and_data_chunks_together(args, source_chunks, data_chunks):
    assert len(source_chunks) >= 2
    assert source_chunks[0].type == 'IHDR'
    assert source_chunks[-1].type == 'IEND'
    with open(args.output, 'wb') as fd:
        fd.write(PNG_SIG)
        for c in source_chunks[0:-1]:
            fd.write(c.raw_data)
        for c in data_chunks:
            fd.write(c.raw_data)
        fd.write(source_chunks[-1].raw_data)


def break_stream_into_bites(stream, compress_method, fernet=None):
    bites = []
    while len(stream.peek(1)) > 0:
        b = stream.read(MAX_DATA_CHUNK_BYTES)
        if compress_method == CompressMethod.No:
            pass
        elif compress_method == CompressMethod.Zlib:
            b = zlib.compress(b)
        else:
            fail_hard('Unknown compress method', compress_method)
        if fernet is not None:
            b = encrypt(fernet, b)
        bites.append(b)
    return bites


def encode_stream_as_chunks(stream, args, compress_method):
    ''' The input stream should contain bytes that the user wishes to encode
    into a PNG. If seekable, seek to the start. Otherwise assume we are at the
    start of the data the user wishes to encode.

    Returns an ordered list of all the chunks that need to be stored in the
    image. '''
    if stream.seekable():
        stream.seek(0, 0)
    if args.encrypt:
        salt, fernet = gen_key()
        encryption_type = EncryptionType.SaltedPass01
    else:
        salt, fernet = None, None
        encryption_type = EncryptionType.No
    bites = break_stream_into_bites(stream, compress_method, fernet)
    index_chunk = [IndexChunk(
        EncodingType.SingleFile, encryption_type, compress_method, len(bites))]
    crypt_info_chunk = [CryptInfoChunk(salt)] if args.encrypt else []
    data_chunks = [DataChunk(bite) for bite in bites]
    return index_chunk + crypt_info_chunk + data_chunks


def get_provided_source_image_chunks(args):
    with open(args.source, 'rb') as fd:
        source_chunks = read_image_stream(fd)
    if len(source_chunks) < 2:
        fail_hard('Don\'t know how to handle image with only',
                  len(source_chunks), 'chunks in it. They\'re', source_chunks)
    if source_chunks[0].type != 'IHDR':
        fail_hard('Don\'t know how to handle image with first chunk type',
                  source_chunks[0].type)
    if source_chunks[-1].type != 'IEND':
        fail_hard('Don\'t know how to handle image with last chunk type',
                  source_chunks[-1].type)
    return source_chunks


def get_basic_source_image_chunks():
    IHDR = Chunk('IHDR', struct.pack('>IIBBBBB', 1, 1, 1, 0, 0, 0, 0))
    IDAT = Chunk('IDAT', zlib.compress(struct.pack('>BB', 0, 0)))
    IEND = Chunk('IEND', b'')
    return [IHDR, IDAT, IEND]


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
    p.add_argument(
        '-c', '--compress', type=str, default='no',
        choices=['no', 'gzip'], help='Compress data before encoding')
    p.add_argument(
        '-e', '--encrypt', action='store_true', help='If specified, encrypt '
        'data before encoding')


def main(args):
    if args.source is not None and not os.path.isfile(args.source):
        fail_hard(args.source, 'must exist')
    if args.compress == 'no':
        compress_method = CompressMethod.No
    elif args.compress == 'gzip':
        compress_method = CompressMethod.Zlib
    else:
        fail_hard('Unknown --compress value', args.compress)
    if args.source:
        source_chunks = get_provided_source_image_chunks(args)
    else:
        source_chunks = get_basic_source_image_chunks()
    with open(args.input, 'rb') as fd:
        chunks = encode_stream_as_chunks(fd, args, compress_method)
    encode_source_and_data_chunks_together(args, source_chunks, chunks)
