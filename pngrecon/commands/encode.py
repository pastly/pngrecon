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
import random


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


def break_into_bites(b, max_bite_len):
    assert isinstance(b, bytes)
    bites = []
    while len(b) > max_bite_len:
        bites.append(b[0:max_bite_len])
        b = b[max_bite_len:]
    if len(b) > 0:
        bites.append(b)
    return bites


def compress_stream(stream, compress_method):
    assert isinstance(compress_method, CompressMethod)
    b = b''
    while len(stream.peek(1)) > 0:
        b += stream.read()
    if compress_method == CompressMethod.No:
        return b
    elif compress_method == CompressMethod.Zlib:
        return zlib.compress(b)


def encrypt_bytes(b, fernet):
    assert isinstance(b, bytes)
    if not fernet:
        return b
    return encrypt(fernet, b)


def get_password(args):
    assert not os.path.isdir(args.password_file)
    with open(args.password_file, 'rb') as fd:
        return fd.read()


def completely_encode_stream(stream, args, compress_method):
    ''' The input stream should contain bytes that the user wishes to encode
    into a PNG. If seekable, seek to the start. Otherwise assume we are at the
    start of the data the user wishes to encode.

    Returns an ordered list of all the chunks that need to be stored in the
    image. '''
    if stream.seekable():
        stream.seek(0, 0)
    if args.encrypt:
        pw = get_password(args)
        salt, fernet = gen_key(password=pw)
        encryption_type = EncryptionType.SaltedPass01
    else:
        salt, fernet = None, None
        encryption_type = EncryptionType.No
    b = encrypt_bytes(compress_stream(stream, compress_method), fernet)
    bites = break_into_bites(b, MAX_DATA_CHUNK_BYTES)
    index_chunk = [IndexChunk(
        EncodingType.SingleFile, encryption_type, compress_method, len(bites))]
    crypt_info_chunk = [CryptInfoChunk(salt)] if args.encrypt else []
    data_chunks = [DataChunk(i, bite) for i, bite in enumerate(bites)]
    all_chunks = index_chunk + crypt_info_chunk + data_chunks
    # This random shuffle is soley for defensive programming against lazy
    # programmers. When an image is edited, the PNG standard allows for chunks
    # to be reordered (to some extent; not completely randomly). Therefore,
    # pngrecon decoders should NOT be expecting our chunks to be in a specific
    # order.
    random.shuffle(all_chunks)
    return all_chunks


def get_provided_source_image_chunks(args):
    with open(args.source, 'rb') as fd:
        source_chunks = read_image_stream(fd)
    if source_chunks is None:
        fail_hard(args.source, 'does not appear to be a PNG')
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
        '-c', '--compress', type=str, default='no', nargs='?',
        choices=['no', 'gzip'], help='Compress data before encoding. If not '
        'specified, do not compress. If specified with no argument, compress '
        'with gzip. Otherwise, compress according to the argument.')
    p.add_argument(
        '-e', '--encrypt', action='store_true', help='If specified, encrypt '
        'data before encoding')
    p.add_argument(
        '--password-file', type=str, default=None,
        help='If encrypting, read password to use for symmetric encryption '
        'from this file.')


def main(args):
    if args.source is not None and not os.path.isfile(args.source):
        fail_hard(args.source, 'must exist')
    if not os.path.exists(args.input):
        fail_hard(args.input, 'must exist')
    if os.path.isdir(args.input):
        fail_hard('Input can\'t be a directory')
    if args.compress == 'no':
        compress_method = CompressMethod.No
    elif args.compress == 'gzip':
        compress_method = CompressMethod.Zlib
    elif args.compress is None:
        compress_method = CompressMethod.Zlib
    else:
        fail_hard('Unknown --compress value', args.compress)
    if args.source:
        source_chunks = get_provided_source_image_chunks(args)
    else:
        source_chunks = get_basic_source_image_chunks()
    if args.encrypt:
        if not args.password_file:
            fail_hard('--password-file must be specified for encryption')
        elif os.path.isdir(args.password_file):
            fail_hard(args.password_file, 'must be a file')
    elif args.password_file:
        fail_hard('Don\'t specify --password-file when not doing encryption')
    with open(args.input, 'rb') as fd:
        chunks = completely_encode_stream(fd, args, compress_method)
    encode_source_and_data_chunks_together(args, source_chunks, chunks)
