import sys


def log(*s):
    print(*s, file=sys.stderr)


def fail_hard(*s):
    if s:
        log(*s)
    exit(1)
