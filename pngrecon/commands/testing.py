from ..lib.chunk import IndexChunk
from ..lib.chunk import (EncodingType, CompressMethod)
from ..util.log import log
from argparse import ArgumentDefaultsHelpFormatter


def gen_parser(sub_p):
    p = sub_p.add_parser(
        'testing', formatter_class=ArgumentDefaultsHelpFormatter)


def main(args):
    c = IndexChunk(EncodingType.SingleFile, CompressMethod.Zlib)
    log(c.encoding_type)
    log(c.compress_method)
    log(c.data)
