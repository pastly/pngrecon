import pngrecon.commands.info
import pngrecon.commands.encode
import pngrecon.commands.decode
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


PNG_RECON_VERSION = '0.2.0'


def create_parser():
    p = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    sub_p = p.add_subparsers(dest='command')
    pngrecon.commands.info.gen_parser(sub_p)
    pngrecon.commands.encode.gen_parser(sub_p)
    pngrecon.commands.decode.gen_parser(sub_p)
    return p


def main():
    parser = create_parser()
    args = parser.parse_args()
    def_args = [args]
    def_kwargs = {}
    known_commands = {
        'info': {'f': pngrecon.commands.info.main,
                 'a': def_args, 'kw': def_kwargs},
        'encode': {'f': pngrecon.commands.encode.main,
                   'a': def_args, 'kw': def_kwargs},
        'decode': {'f': pngrecon.commands.decode.main,
                   'a': def_args, 'kw': def_kwargs},
    }
    try:
        if args.command not in known_commands:
            parser.print_help()
        else:
            comm = known_commands[args.command]
            exit(comm['f'](*comm['a'], **comm['kw']))
    except KeyboardInterrupt:
        print('')
