#!/usr/bin/env python3
"""Bounded, exact typed JSON snapshot comparison. Standard library only."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON numbers are not supported')


def load(path):
    with Path(path).open('rb') as f:
        data = f.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError('snapshot exceeds 8 MiB')
    value = json.loads(data, object_pairs_hook=unique, parse_float=Decimal, parse_constant=reject_constant)
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 128:
            raise ValueError('snapshot exceeds 128 nesting levels')
        if isinstance(item, (list, dict)):
            pending.extend((v, depth + 1) for v in (item.values() if isinstance(item, dict) else item))
    return value, hashlib.sha256(data).hexdigest()


def pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def display(value):
    # Tag every value so a decimal cannot impersonate a user-authored object.
    if isinstance(value, Decimal):
        return {'type': 'decimal', 'value': str(value)}
    if isinstance(value, list):
        return {'type': 'array', 'value': [display(v) for v in value]}
    if isinstance(value, dict):
        return {'type': 'object', 'value': {k: display(v) for k, v in value.items()}}
    kind = 'null' if value is None else 'boolean' if isinstance(value, bool) else 'integer' if isinstance(value, int) else 'string'
    return {'type': kind, 'value': value}


def diff(before, after, maximum=200):
    changes, count = [], 0

    def record(kind, path, **values):
        nonlocal count
        count += 1
        if len(changes) < maximum:
            changes.append({'kind': kind, 'path': path, **{k: display(v) for k, v in values.items()}})

    def walk(a, b, path):
        if type(a) is not type(b):
            record('changed', path, before=a, after=b)
        elif isinstance(a, dict):
            for key in sorted(a.keys() | b.keys()):
                child = pointer(path, key)
                if key not in a: record('added', child, after=b[key])
                elif key not in b: record('removed', child, before=a[key])
                else: walk(a[key], b[key], child)
        elif isinstance(a, list):
            for i in range(max(len(a), len(b))):
                child = pointer(path, i)
                if i >= len(a): record('added', child, after=b[i])
                elif i >= len(b): record('removed', child, before=a[i])
                else: walk(a[i], b[i], child)
        elif a != b:
            record('changed', path, before=a, after=b)

    walk(before, after, '')
    return {'schema_version': 1, 'total_changes': count, 'truncated': count > len(changes), 'changes': changes}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('before'); p.add_argument('after')
    p.add_argument('--max-changes', type=int, default=200); p.add_argument('--check', action='store_true')
    a = p.parse_args()
    try:
        if not 1 <= a.max_changes <= 10000:
            raise ValueError('max-changes must be 1–10000')
        before, bh = load(a.before); after, ah = load(a.after)
        result = diff(before, after, a.max_changes)
        result.update({'before_sha256': bh, 'after_sha256': ah})
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return int(a.check and result['total_changes'] > 0)
    except (OSError, ValueError, TypeError, RecursionError) as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
