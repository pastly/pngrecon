#!/usr/bin/env python3
## Script that uses pngrecon to encode a directory (recursively) into images.
##
## Requires a key for encryption. Create it with something like:
##
##     head -c 32 /dev/urandom > filler.key
##
## See filler.conf in this directory for an example configuration file for this
## script. Run like this:
##
##     python3 filler.py filler.conf
##
import configparser
import sqlite3
import subprocess
import os
import sys
import glob
import hashlib
import time
import pathlib
from dataclasses import dataclass
from typing import List, Union
from copy import deepcopy
from tempfile import TemporaryFile

BUNDLE_LEAF_DIR = 1
SPLIT_FILE = 2

def log(*a, **kw):
    print(*a, file=sys.stderr, **kw)

@dataclass
class PathComponent:
    s: str

    def __str__(self):
        return self.s

@dataclass
class Path:
    items: List[PathComponent]
    absolute: bool

    def __str__(self):
        s = '/'.join([str(i) for i in self.items])
        if self.absolute:
            s = '/' + s
        return s
    
    def __getitem__(self, i):
        return self.items[i]

    def append(self, p: Union[PathComponent, 'Path']):
        if isinstance(p, PathComponent):
            self.items.append(p)
            return
        self.items.extend(p.items)

    @staticmethod
    def from_str(s: str):
        pcs = [PathComponent(i) for i in s.split('/')]
        absolute = s.startswith('/')
        if absolute:
            assert not pcs[0].s
            pcs = pcs[1:]
        return Path(pcs, absolute)

@dataclass
class Root:
    in_p: Path
    out_p: Path
    opts: dict

def get_dir_size(d: Path):
    dname = str(d)
    if not os.path.exists(dname):
        return 0
    args = ['du', '--bytes', '-s', dname]
    out = subprocess.run(args, capture_output=True, text=True).stdout.split()[0]
    return int(out)


def get_roots(conf) -> List[Root]:
    a = []
    for key in conf['roots'].keys():
        opts1 = conf[key + '_options']
        opts = {
            'outdir_size_limit': int(float(opts1['outdir_size_limit_mb']) * 1024 * 1024),
            'split_file_size_limit': int(float(opts1['split_file_size_limit_mb']) * 1024 * 1024) \
                if 'split_file_size_limit_mb' in opts1 \
                else 1 * 1024 * 1024 * 1024, # 1 GiB
            'style': {
                'bundle_leaf_dir': BUNDLE_LEAF_DIR,
                'split_file': SPLIT_FILE,
            }[opts1['style']],
        }
        a.append(Root(
            Path.from_str(os.path.abspath(conf['roots'][key])),
            Path.from_str(os.path.abspath(opts1['output'])),
            opts,
        ))
    return a


def insert_roots(db_con, roots: List[Root]):
    cur = db_con.cursor()
    for root in roots:
        p = str(root.in_p)
        res = cur.execute('SELECT 1 FROM name_map WHERE name = ? LIMIT 1', (p,))
        if res.fetchone() is None:
            cur.execute('INSERT INTO name_map VALUES (?, NULL)', (p,))
    db_con.commit()

# should only be used on a root because only roots are unique
def get_root_rowid(db_con, root: Root):
    cur = db_con.cursor()
    res = cur.execute('SELECT rowid FROM name_map WHERE name = ?', (str(root.in_p),)).fetchone()
    assert res is not None
    return res[0]

def walk_roots(db_con, roots: List[Root]):
    cur = db_con.cursor()
    # subpath (without parentdir), parentdir,      rowid, options
    # Path,                        Optional<Path>, int,   dict
    todo = [(r.in_p, None, get_root_rowid(db_con, r), r.opts) for r in roots]
    while len(todo):
        current, parent, cur_rowid, opts = todo.pop()
        if parent:
            p = pathlib.Path(str(parent), str(current))
        else:
            p = pathlib.Path(str(current))
        for sub in p.glob('*'):
            if not (sub.is_dir() or (sub.is_file() and opts['style'] == SPLIT_FILE)):
                continue
            sub_relative = str(sub).removeprefix(str(p) + '/')
            res = cur.execute(
                'SELECT rowid FROM name_map WHERE name = ? AND parent = ?',
                (sub_relative, cur_rowid)).fetchone()
            if res is None:
                res = cur.execute(
                    'INSERT INTO name_map VALUES (?, ?)',
                    (sub_relative, cur_rowid))
                new_rowid = cur.lastrowid
            else:
                new_rowid = res[0]
            todo.append((Path.from_str(sub_relative), Path.from_str(str(p)), new_rowid, opts))
    db_con.commit()


def get_path(db_con, rowid):
    cur = db_con.cursor()
    row = cur.execute('SELECT rowid, * FROM name_map WHERE rowid = ?', (rowid,)).fetchone()
    if row['parent']:
        root, subpath, ids = get_path(db_con, row['parent'])
        subpath.append(PathComponent(row['name']))
        ids.append(row['rowid'])
        return root, subpath, ids
    root = Path.from_str(row['name'])
    return root, Path([], False), [row['rowid']]


def insert_work(db_con):
    cur = db_con.cursor()
    # find all leaf dirs/files (are not the parent of anything) that also don't exist
    # in work table
    res = cur.execute('''
        SELECT rowid FROM name_map nm
        WHERE NOT EXISTS (SELECT 1 FROM name_map WHERE parent = nm.rowid LIMIT 1)
        AND NOT EXISTS (SELECT 1 FROM work WHERE obj_id = nm.rowid LIMIT 1)
    ''')
    for a in res.fetchall():
        #log(get_path(db_con, a['rowid']))
        cur.execute('INSERT INTO work VALUES (?, ?)', (a['rowid'], False))
    db_con.commit()

def next_work(db_con):
    cur = db_con.cursor()
    cur.execute('SELECT rowid, * FROM work WHERE is_done = FALSE LIMIT 1')
    return cur.fetchone()

def encode(root: Root, in_name: Path, out_fname: Path, pngrecon, keyfile):
    tar_args = ['tar', '-c', '-C', str(root.in_p), str(in_name)]
    png_args = [pngrecon, 'encode', '-e', '--key-file', keyfile, '-o', str(out_fname)]
    tar = subprocess.Popen(tar_args, stdout=subprocess.PIPE)
    png = subprocess.run(png_args, stdin=tar.stdout)
    return png.returncode == 0

def split_encode(root: Root, in_name: Path, out_dname: Path, pngrecon, keyfile, max_file_size: int):
    in_f = deepcopy(root.in_p)
    in_f.append(in_name)
    in_fd = open(str(in_f), 'rb')
    eof = False
    n = 1
    buf_size = 4 * 1024 * 1024
    while not eof:
        with TemporaryFile() as tmp_fd:
            budget = max_file_size
            while budget > 0 and not eof:
                b = in_fd.read(min(buf_size, budget))
                if not len(b):
                    eof = True
                    break
                tmp_fd.write(b)
                budget -= len(b)
            if not len(b) and n > 1:
                # n > 1 check because for empty files I've decided we want to
                # output an image
                continue
            tmp_fd.seek(0, 0)
            out_f = deepcopy(out_dname)
            out_f.append(PathComponent(f'{n:03}.png'))
            png_args = [pngrecon, 'encode', '-e', '--key-file', keyfile, '-o', str(out_f)]
            png = subprocess.run(png_args, stdin=tmp_fd)
            if png.returncode != 0:
                return False
        n += 1
    return True


def main(conf):
    db_con = sqlite3.connect(conf['db']['fname'])
    db_con.row_factory = sqlite3.Row
    cur = db_con.cursor()
    cur.executescript('''
        BEGIN;
        CREATE TABLE IF NOT EXISTS name_map(
            name NOT NULL,
            parent INTEGER,
            FOREIGN KEY (parent) REFERENCES name_map (rowid)
        );
        CREATE TABLE IF NOT EXISTS work(
            obj_id INTEGER NOT NULL,
            is_done BOOLEAN NOT NULL,
            FOREIGN KEY (obj_id) REFERENCES name_map (rowid)
        );
        CREATE TABLE IF NOT EXISTS encoded_location(
            fname NOT NULL,
            obj_id INTEGER NOT NULL,
            backup_style INTEGER NOT NULL,
            FOREIGN KEY (obj_id) REFERENCES name_map (rowid)
        );
        COMMIT;
    ''')
    roots = get_roots(conf)
    insert_roots(db_con, roots)
    walk_roots(db_con, roots)
    insert_work(db_con)
    row = next_work(db_con)
    while row:
        root_path, subpath, id_path = get_path(db_con, row['obj_id'])
        root = [r for r in roots if r.in_p == root_path][0]
        if get_dir_size(root.out_p) > root.opts['outdir_size_limit']:
            log(str(root.out_p), 'too big')
            time.sleep(30)
            continue
        out_dname = deepcopy(root.out_p)
        out_dname.append(Path([str(_) for _ in id_path[:-1]], False))
        if root.opts['style'] == BUNDLE_LEAF_DIR:
            os.makedirs(str(out_dname), exist_ok=True)
            out_fname = deepcopy(out_dname)
            out_fname.append(PathComponent(str(id_path[-1]) + '.png'))
            log('Doing', subpath, 'into', out_fname)
            did_ok = encode(
                root, subpath, out_fname,
                conf['pngrecon']['path'],
                conf['pngrecon']['keyfile'],
            )
        elif root.opts['style'] == SPLIT_FILE:
            out_dname.append(PathComponent(str(id_path[-1])))
            os.makedirs(str(out_dname), exist_ok=True)
            log('Doing', subpath, 'into', out_dname)
            did_ok = split_encode(
                root, subpath, out_dname,
                conf['pngrecon']['path'],
                conf['pngrecon']['keyfile'],
                root.opts['split_file_size_limit'],
            )
        else:
            assert False
        if did_ok:
            cur.execute('BEGIN')
            cur.execute('UPDATE work SET is_done = TRUE WHERE rowid = ?', (row['rowid'],))
            cmds = []
            if root.opts['style'] == BUNDLE_LEAF_DIR:
                p = deepcopy(root.in_p)
                p.append(subpath)
                for fname in pathlib.Path(str(p)).glob('*'):
                    cmds.append((os.path.basename(fname), id_path[-1], root.opts['style']))
            elif root.opts['style'] == SPLIT_FILE:
                cmds.append((os.path.basename(str(subpath)), id_path[-1], root.opts['style']))
            else:
                assert False
            cur.executemany('INSERT INTO encoded_location VALUES(?, ?, ?)', cmds)
            cur.execute('COMMIT')
        else:
            log('didnt do ok :(')
            return 1
        row = next_work(db_con)
    return 0

if __name__ == '__main__':
    c = configparser.ConfigParser()
    c.read(sys.argv[1])
    exit(main(c))