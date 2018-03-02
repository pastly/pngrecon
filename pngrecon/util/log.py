import sys


def log_stderr(*s):
    print(*s, file=sys.stderr)


def log_stdout(*s):
    print(*s)


def fail_hard(*s):
    if s:
        log_stderr(*s)
    exit(1)
