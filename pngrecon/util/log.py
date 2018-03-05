import sys


def log_stderr(*a, **kw):
    print(*a, file=sys.stderr, **kw)


def log_stdout(*a, **kw):
    print(*a, **kw)


def fail_hard(*a, **kw):
    if a:
        log_stderr(*a, **kw)
    exit(1)
