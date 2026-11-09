---
name: draconitic-snapshot-diff
description: Compare two supplied local JSON snapshots with typed changes at JSON Pointer paths. Use to review API, configuration, catalog, or research snapshot changes; not to fetch URLs or infer semantic identity between reordered arrays.
license: MIT
---

Requires: Python 3.10 or newer and local file execution.


Run `scripts/snapshot_diff.py` relative to this skill's installed directory:

```bash
python3 scripts/snapshot_diff.py /path/to/before.json /path/to/after.json
python3 scripts/snapshot_diff.py /path/to/before.json /path/to/after.json --max-changes 50 --check
```

Inputs remain local and unchanged. Reports contain changed values, so review them before sharing. The helper rejects duplicate object keys, non-finite numbers, inputs above 8 MiB, and nesting beyond 128 levels. It distinguishes booleans, integers, decimals, strings, arrays, objects, and null. Numeric lexical forms with equal decimal value compare equally within the same numeric type; large numbers are compared exactly.

Arrays compare by index. If the real identity is a field such as `id`, first create explicit derived snapshots keyed by that field, detect duplicate IDs, and retain the original inputs. Do not silently sort an array whose order matters. Missing fields differ from fields set to null. Report truncation with the exact total change count; never imply the displayed subset is complete.

Exit 0 means completed (and, with `--check`, unchanged); exit 1 means differences with `--check`; exit 2 means invalid input. Explain observed changes and source timestamps separately. A snapshot difference does not establish why the source changed or that either snapshot is authoritative.
