#!/usr/bin/env python
import argparse
import shutil
import os
from pathlib import Path


USER_DIR = Path(__file__).parent / 'user'
HOME_USER_DIR = Path.home() / '.talon/user'


parser = argparse.ArgumentParser(description='Install Talon extension scripts.')
parser.add_argument('-s', '--symlink', action='store_true', help='Create symlinks instead of copying the scripts.')
parser.add_argument('-f', '--force', action='store_true', help='Force install. Replaces files that previously existed.')
args = parser.parse_args()


def copy_file(src):
    dst_file = HOME_USER_DIR / src.name
    if (dst_file.is_file() or dst_file.is_symlink()) and not args.force:
        print(f'File {dst_file} already exists. Skipping. If you wish to replace it, rerun with --force')
        return
    if args.symlink:
        if dst_file.is_file() or dst_file.is_symlink():
            os.remove(dst_file)
        os.symlink(src.resolve(), dst_file)
    else:
        shutil.copy(src, HOME_USER_DIR)


for script in USER_DIR.glob('*.py'):
    copy_file(script)
