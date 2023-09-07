from ..lib.chunk import read_image_stream
from ..lib.chunk import (CompressMethod, EncodingType, EncryptionType)
from ..lib.chunk import (PNG_SIG, TARGET_MAX_BUFFER_BYTES)
from ..lib.chunk import (Chunk, IndexChunk, DataChunk, CryptInfoChunk)
from ..util.log import fail_hard
from ..util.crypto import gen_key
from ..util.crypto import encrypt
from argparse import ArgumentDefaultsHelpFormatter
import os
import struct
import zlib
import lzma
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


def break_into_bites(iter, max_bite_len):
    b = b''
    for i in iter:
        b += i
        while len(b) > max_bite_len:
            yield b[0:max_bite_len]
            b = b[max_bite_len:]
    if len(b) > 0:
        yield b


def compress_stream(stream, compress_method, max_size):
    assert isinstance(compress_method, CompressMethod)
    if compress_method == CompressMethod.Zlib:
        compressor = zlib.compressobj()
    elif compress_method == CompressMethod.Lzma:
        compressor = lzma.LZMACompressor()
    else:
        assert compress_method == CompressMethod.No
        compressor = None
    b = b''
    while len(stream.peek(1)) > 0:
        b = stream.read(max_size)
        if compressor:
            data = compressor.compress(b)
            if len(data):
                yield data
        else:
            yield b
    if compressor:
        data = compressor.flush()
        if len(data):
            yield data


def encrypt_bytes(iter, fernet, max_size):
    if not fernet:
        for i in iter:
            yield i
    else:
        b = b''
        for i in iter:
            b += i
            while len(b) > max_size:
                yield encrypt(fernet, b[:max_size])
                b = b[max_size:]
        if len(b):
            yield encrypt(fernet, b)


def completely_encode_stream(stream, args, compress_method):
    ''' The input stream should contain bytes that the user wishes to encode
    into a PNG. If seekable, seek to the start. Otherwise assume we are at the
    start of the data the user wishes to encode.

    Returns an ordered list of all the chunks that need to be stored in the
    image. '''
    if stream.seekable():
        stream.seek(0, 0)
    if args.encrypt:
        pw = None
        if args.key_file:
            with open(args.key_file, 'rb') as fd:
                pw = fd.read()
        salt, fernet = gen_key(password=pw)
        encryption_type = EncryptionType.SaltedPass01
    else:
        salt, fernet = None, None
        encryption_type = EncryptionType.No
    b = encrypt_bytes(
        compress_stream(stream, compress_method, args.buffer_max_bytes),
        fernet,
        args.buffer_max_bytes)
    #bites = break_into_bites(b, args.buffer_max_bytes)
    bites = b
    if args.encrypt:
        yield CryptInfoChunk(salt)
    n = 0
    for i, bite in enumerate(bites):
        yield DataChunk(i, bite)
        n += 1
    yield IndexChunk(EncodingType.SingleFile, encryption_type, compress_method, n)
    #################################################
    #crypt_info_chunk = [CryptInfoChunk(salt)] if args.encrypt else []
    #data_chunks = [DataChunk(i, bite) for i, bite in enumerate(bites)]
    #index_chunk = [IndexChunk(
    #    EncodingType.SingleFile, encryption_type, compress_method, len(data_chunks))]
    #all_chunks = index_chunk + crypt_info_chunk + data_chunks
    ## This random shuffle is soley for defensive programming against lazy
    ## programmers. When an image is edited, the PNG standard allows for chunks
    ## to be reordered (to some extent; not completely randomly). Therefore,
    ## pngrecon decoders should NOT be expecting our chunks to be in a specific
    ## order.
    #random.shuffle(all_chunks)
    #return all_chunks


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
        choices=['no', 'gzip', 'xz'], help='Compress data before encoding. If '
        'not specified, do not compress. If specified with no argument, '
        'compress with gzip. Otherwise, compress according to the argument.')
    p.add_argument(
        '-e', '--encrypt', action='store_true', help='If specified, encrypt '
        'data before encoding')
    p.add_argument(
        '--key-file', type=str, default=None,
        help='If encrypting, read key to use for symmetric encryption '
        'from this file.')
    p.add_argument(
        '--buffer-max-bytes', type=int, default=TARGET_MAX_BUFFER_BYTES,
        help='Target maximum nubmer of bytes to encode at once. Weird (but '
        'safe) stuff happens with highly compressible data.')


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
    elif args.compress == 'xz':
        compress_method = CompressMethod.Lzma
    elif args.compress is None:
        compress_method = CompressMethod.Zlib
    else:
        fail_hard('Unknown --compress value', args.compress)

    if args.source:
        source_chunks = get_provided_source_image_chunks(args)
    else:
        source_chunks = get_basic_source_image_chunks()

    if args.encrypt:
        if args.key_file is not None and os.path.isdir(args.key_file):
            fail_hard(args.key_file, 'must be a file')
    elif args.key_file:
        fail_hard('Don\'t specify --key-file when not doing encryption')

    with open(args.input, 'rb') as fd:
        chunks = completely_encode_stream(fd, args, compress_method)
        encode_source_and_data_chunks_together(args, source_chunks, chunks)
