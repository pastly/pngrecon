#!/usr/bin/env python3
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from lib.chunk import read_image_stream


def log(*s):
    print(*s)


def fail_hard(*s):
    if s:
        log(*s)
    exit(1)


def main(args):
    with open(args.image, 'rb') as fd:
        chunks = read_image_stream(fd)
    log(args.image, 'contains', len(chunks), 'chunks')
    for c in chunks:
        log('Chunk', c.type, 'with len', c.length)


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('image', type=str, help='Path to image to learn about')
    args = parser.parse_args()
    if not os.path.isfile(args.image):
        fail_hard(args.image, 'must exist')
    main(args)
