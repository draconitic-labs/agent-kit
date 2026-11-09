#!/usr/bin/env python3
"""Explicit-file evidence bundles. Standard library only; no network access."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
from urllib.parse import urlsplit

MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILES = 1000
BLOCKED = {'.env', '.netrc', '.npmrc', '.pypirc', 'credentials', 'credentials.json',
           'id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa', '.git-credentials', '.pgpass'}
BLOCKED_DIRS = {'.git', '.ssh', '.aws', '.gnupg', '.kube'}
BLOCKED_SEQUENCES = [('.docker', 'config.json'), ('.config', 'gh')]


def relative(value):
    p = PurePosixPath(value)
    if (not value or '\\' in value or p.is_absolute() or '..' in p.parts
            or '.' in p.parts or ':' in value or p.as_posix() != value):
        raise ValueError('paths must be normalized relative POSIX paths')
    return p


def checked_file(root, value):
    p = relative(value)
    cur = root
    for part in p.parts:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError('symlinks are not accepted')
    if not cur.is_file() or not stat.S_ISREG(cur.stat().st_mode):
        raise ValueError('input must be a regular file')
    if not cur.resolve().is_relative_to(root.resolve()):
        raise ValueError('file escapes root')
    return cur


def sensitive(value):
    parts = [part.lower() for part in relative(value).parts]
    for low in parts:
        if (low in BLOCKED or low.startswith('.env.') or low.endswith(('.pem', '.key', '.secret', '.p12', '.pfx'))
                or low in BLOCKED_DIRS):
            raise ValueError('credential-like path refused; review selected files manually')
    for first, second in BLOCKED_SEQUENCES:
        if any(a == first and b == second for a, b in zip(parts, parts[1:])):
            raise ValueError('credential-like path refused; review selected files manually')


def read_bounded(path):
    # O_NOFOLLOW protects the final component on systems that provide it.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
            raise ValueError('file is not regular or exceeds 64 MiB')
        data = f.read(MAX_FILE + 1)
        after = os.fstat(f.fileno())
    if (len(data) > MAX_FILE or len(data) != before.st_size
            or (before.st_size, before.st_mtime_ns, before.st_ino) !=
               (after.st_size, after.st_mtime_ns, after.st_ino)):
        raise ValueError('file changed during collection or exceeds limit')
    return data


def create(root, files, out, sources):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not files or len(files) > MAX_FILES or len(set(files)) != len(files):
        raise ValueError('select 1–1000 unique files under a directory')
    for url in sources:
        u = urlsplit(url)
        if u.scheme not in {'http', 'https'} or not u.hostname or u.username or u.password:
            raise ValueError('source URLs must be public HTTP(S) URLs without user information')
        if u.query or u.fragment:
            raise ValueError('source URLs must omit query strings and fragments')
    out = Path(out).absolute()
    if os.path.lexists(out):
        raise ValueError('output already exists')
    out.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the output first. On failure remove only our own new directory.
    out.mkdir()
    try:
        records, total = [], 0
        for value in sorted(files):
            sensitive(value)
            data = read_bounded(checked_file(root, value))
            total += len(data)
            if total > MAX_TOTAL:
                raise ValueError('bundle exceeds 256 MiB')
            target = out / 'files' / value
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as f:
                f.write(data)
            records.append({'path': value, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest = {'schema_version': 1, 'algorithm': 'sha256', 'sources': sorted(set(sources)), 'files': records}
        data = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
        (out / 'manifest.json').write_bytes(data)
        return {'files': len(records), 'bytes': total, 'manifest_sha256': hashlib.sha256(data).hexdigest()}
    except BaseException:
        shutil.rmtree(out)
        raise


def verify(bundle):
    bundle = Path(bundle)
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('bundle must be a regular directory')
    manifest_bytes = read_bounded(checked_file(bundle, 'manifest.json'))
    manifest = json.loads(manifest_bytes)
    if (not isinstance(manifest, dict) or manifest.get('schema_version') != 1
            or manifest.get('algorithm') != 'sha256' or not isinstance(manifest.get('files'), list)
            or not 1 <= len(manifest['files']) <= MAX_FILES):
        raise ValueError('unsupported manifest')
    expected, total = {'manifest.json'}, 0
    for item in manifest['files']:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('invalid manifest file record')
        path = 'files/' + str(relative(item['path']))
        if path in expected:
            raise ValueError('duplicate manifest path')
        expected.add(path)
        data = read_bounded(checked_file(bundle, path))
        total += len(data)
        if total > MAX_TOTAL or len(data) != item.get('bytes') or hashlib.sha256(data).hexdigest() != item.get('sha256'):
            raise ValueError('bundle size or digest mismatch')
    actual = set()
    def traversal_error(error):
        raise error

    for base, dirs, files in os.walk(bundle, followlinks=False, onerror=traversal_error):
        for name in dirs + files:
            path = Path(base) / name
            if path.is_symlink():
                raise ValueError('symlink in bundle')
        for name in files:
            actual.add((Path(base) / name).relative_to(bundle).as_posix())
    if actual != expected:
        raise ValueError('unexpected or missing bundle files')
    return {'valid': True, 'files': len(manifest['files']), 'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('create')
    c.add_argument('--root', required=True)
    c.add_argument('--file', action='append', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--source', action='append', default=[])
    v = sub.add_parser('verify'); v.add_argument('bundle')
    args = parser.parse_args()
    try:
        result = create(args.root, args.file, args.out, args.source) if args.command == 'create' else verify(args.bundle)
        print(json.dumps(result, indent=2)); return 0
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
