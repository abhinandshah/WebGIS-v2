#!/usr/bin/env python3
"""Create the .env file: a fresh SECRET_KEY plus hashed login passwords.

    python tools/init_env.py                 # asks for both passwords
    python tools/init_env.py --random        # generates passwords and prints them once
    python tools/init_env.py --force         # overwrite an existing .env

Passwords are stored only as salted hashes; the plain text is never written
to disk.
"""
import argparse
import getpass
import os
import secrets
import stat
import sys

from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, '.env')
MIN_LEN = 10


def ask(label):
    while True:
        pw = getpass.getpass(f'Password for "{label}" (min {MIN_LEN} chars): ')
        if len(pw) < MIN_LEN:
            print(f'  Too short - use at least {MIN_LEN} characters.')
            continue
        if pw != getpass.getpass('  Repeat password: '):
            print('  Passwords did not match.')
            continue
        return pw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--random', action='store_true', help='generate random passwords and print them once')
    ap.add_argument('--force', action='store_true', help='overwrite an existing .env')
    args = ap.parse_args()

    if os.path.exists(ENV_PATH) and not args.force:
        sys.exit(f'{ENV_PATH} already exists. Use --force to replace it.')

    if args.random:
        admin_pw, user_pw = secrets.token_urlsafe(12), secrets.token_urlsafe(12)
        print(f'admin password: {admin_pw}\nuser  password: {user_pw}\n(shown once - store them safely)')
    else:
        admin_pw, user_pw = ask('admin'), ask('user')

    lines = [
        f'SECRET_KEY={secrets.token_hex(32)}',
        f"ADMIN_PASSWORD_HASH='{generate_password_hash(admin_pw)}'",
        f"USER_PASSWORD_HASH='{generate_password_hash(user_pw)}'",
        '',
    ]
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    try:
        os.chmod(ENV_PATH, stat.S_IRUSR | stat.S_IWUSR)   # owner-only (no effect on Windows)
    except OSError:
        pass
    print(f'Wrote {ENV_PATH}')


if __name__ == '__main__':
    main()
