from ..lib.chunk import read_image_stream
from ..lib.chunk import (ChunkType, EncryptionType, CompressMethod)
from ..lib.chunk import (IndexChunk, DataChunk, CryptInfoChunk)
from ..util.log import fail_hard
from ..util.crypto import gen_key
from ..util.crypto import decrypt
from argparse import ArgumentDefaultsHelpFormatter
import zlib
import lzma
import os


def gen_parser(sub_p):
    p = sub_p.add_parser(
        'decode', formatter_class=ArgumentDefaultsHelpFormatter)
    p.add_argument('-i', '--input', type=str, default='/dev/stdin',
                   help='Where to read data')
    p.add_argument('-o', '--output', type=str, default='/dev/stdout',
                   help='Where to write data')
    p.add_argument(
        '--password-file', type=str, default=None,
        help='If the data was encrypted, read decryption password  '
        'from this file.')


def keep_and_parse_our_chunks(chunks):
    ''' Given a list of chunks, discard ones that aren't ours and parse
    them from Chunk instances into the more specific types of chunks they
    are '''
    keep_chunks = []
    for chunk in chunks:
        # TODO: Determining if a chunk is one we care about by using exceptions
        # is ugly. It may even be uncomfortably slow. Replace with something
        # better. One idea: an lre_cache'ed function that catches exceptions
        try:
            ChunkType(chunk.type)
        except ValueError:
            continue
        chunk_type = ChunkType(chunk.type)
        if chunk_type == ChunkType.Index:
            keep_chunks.append(IndexChunk.from_chunk(chunk))
        elif chunk_type == ChunkType.Data:
            keep_chunks.append(DataChunk.from_chunk(chunk))
        elif chunk_type == ChunkType.CryptInfo:
            keep_chunks.append(CryptInfoChunk.from_chunk(chunk))
        else:
            fail_hard('Unknown chunk type', chunk_type)
    return keep_chunks


def validate_chunk_set(chunks):
    ''' Given a list of chunks that are all subclasses of Chunk, make sure
    they seem to form a valid set of chunks. For example, the number of data
    chunks is correct, and if encryption is done, there's one encryption info
    chunk. '''
    index_chunks = [c for c in chunks if isinstance(c, IndexChunk)]
    if len(index_chunks) < 1:
        return False, 'There is no index chunk'
    if len(index_chunks) > 1:
        return False, 'There is more than one index chunk'
    index_chunk = index_chunks[0]
    expected_num_data_chunks = index_chunk.num_data_chunks
    data_chunks = [c for c in chunks if isinstance(c, DataChunk)]
    if len(data_chunks) != expected_num_data_chunks:
        return False, 'Expected {} data chunks but there are {}'.format(
            expected_num_data_chunks, len(data_chunks))
    data_chunk_indexes = [c.index for c in data_chunks]
    if len(data_chunk_indexes) != len(set(data_chunk_indexes)):
        return False, 'The data chunk indexes are not unique and they can\'t '\
            'be ordered'
    if index_chunk.encryption_type != EncryptionType.No:
        crypt_info_chunks = [c for c in chunks
                             if isinstance(c, CryptInfoChunk)]
        if len(crypt_info_chunks) != 1:
            return False, 'Data is encrypted. Expected 1 crypt info chunk '\
                'but got {}'.format(len(crypt_info_chunks))
    for i, chunk in enumerate(chunks):
        if not chunk.is_valid:
            return False, 'Invalid {} at index {}'.format(type(chunk), i)
    return True, ''


def get_index_chunk_from_chunks(chunks):
    ''' Given a validated list of chunks, find the index chunk and return it
    '''
    valid, error_msg = validate_chunk_set(chunks)
    assert valid
    index_chunks = [c for c in chunks if isinstance(c, IndexChunk)]
    assert len(index_chunks) == 1
    return index_chunks[0]


def get_crypt_info_chunk_from_chunks(chunks):
    ''' Given a validated list of chunks, find the crypt info chunk and return
    it '''
    valid, error_msg = validate_chunk_set(chunks)
    assert valid
    crypt_info_chunks = [c for c in chunks if isinstance(c, CryptInfoChunk)]
    assert len(crypt_info_chunks) == 1
    return crypt_info_chunks[0]


def decrypt_data(chunks, pw):
    ''' Given a validated list of chunks, decrypt the data in the data chunks
    and return a list of the resulting data '''
    valid, error_msg = validate_chunk_set(chunks)
    assert valid
    index_chunk = get_index_chunk_from_chunks(chunks)
    data_chunks = [c for c in chunks if isinstance(c, DataChunk)]
    data_chunks = sorted(data_chunks, key=lambda c: c.index)
    data = b''.join([c.data for c in data_chunks])
    t = index_chunk.encryption_type
    if t == EncryptionType.No:
        return data
    elif t == EncryptionType.SaltedPass01:
        crypt_info_chunk = get_crypt_info_chunk_from_chunks(chunks)
        salt = crypt_info_chunk.salt
        salt, fernet = gen_key(password=pw, salt=salt)
        return decrypt(fernet, data)
    else:
        fail_hard('Unimplemented decryption type', t)


def decompress_data(index_chunk, data):
    ''' Given a valid index chunk and data from data chunks,
    decompress the bites if necessary. Return a list of the resulting data '''
    assert isinstance(data, bytes)
    assert index_chunk.is_valid
    m = index_chunk.compress_method
    if m == CompressMethod.No:
        return data
    elif m == CompressMethod.Zlib:
        return zlib.decompress(data)
    elif m == CompressMethod.Lzma:
        return lzma.decompress(data)
    else:
        fail_hard('Unimplemented compress method', m)


def completely_decode_chunks(chunks, pw):
    ''' Given a validated list of chunks, decyrpt/decompress as needed and
    return the bytes stored within '''
    valid, error_msg = validate_chunk_set(chunks)
    assert valid
    index_chunk = get_index_chunk_from_chunks(chunks)
    data = decrypt_data(chunks, pw)
    data = decompress_data(index_chunk, data)
    return data


def data_is_encrypted(chunks):
    valid, error_msg = validate_chunk_set(chunks)
    assert valid
    index_chunk = get_index_chunk_from_chunks(chunks)
    return index_chunk.encryption_type != EncryptionType.No


def get_password(args):
    if args.password_file is None:
        fail_hard('Data is encrypted but not --password-file given')
    elif os.path.isdir(args.password_file):
        fail_hard(args.password_file, 'must be a file')
    with open(args.password_file, 'rb') as fd:
        return fd.read()


def main(args):
    if not os.path.exists(args.input):
        fail_hard(args.input, 'must exist')
    if os.path.isdir(args.input):
        fail_hard('Input can\'t be a directory')
    with open(args.input, 'rb') as fd:
        chunks = read_image_stream(fd)
    if chunks is None:
        fail_hard(args.input, 'does not appear to be a PNG')
    chunks = keep_and_parse_our_chunks(chunks)
    valid, error_msg = validate_chunk_set(chunks)
    if not valid:
        fail_hard(error_msg)
    if data_is_encrypted(chunks):
        pw = get_password(args)
    else:
        pw = None
    data = completely_decode_chunks(chunks, pw)
    with open(args.output, 'wb') as fd:
        fd.write(data)
