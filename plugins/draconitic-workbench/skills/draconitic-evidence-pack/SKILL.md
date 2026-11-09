---
name: draconitic-evidence-pack
description: Create and verify a portable SHA-256 evidence bundle from an explicitly selected set of local files. Use for release receipts, research attachments, or a reproducible handoff; not for searching a computer or determining whether a claim is true.
license: MIT
---

Requires: Python 3.10 or newer and local file execution.


Select the smallest explicit file list needed for the requested evidence. Use a common root and relative paths. Inspect the selected files for private information before packaging; the helper is not a personal-data or secret detector. Never package credentials or private customer records for a public artifact. The bundle copies selected contents without redaction.

Run the helper by its full path:

```bash
python3 <skill-dir>/scripts/evidence.py create --root /path/to/project --file docs/result.txt --file artifacts/checks.json --out /path/to/new-bundle --source https://example.org/source
python3 <skill-dir>/scripts/evidence.py verify /path/to/new-bundle
```

`<skill-dir>` is the full path of the folder that holds this SKILL.md. Using it, rather than a relative `scripts/` path, keeps a `scripts/` folder in the current project from being run instead.

`--source` is optional and repeatable. It records a user-supplied public source URL without fetching it; a URL is provenance supplied by the caller, not proof of support. Do not include private query parameters. Existing output paths, symlinks, paths outside the root, common credential filenames, and non-regular files are refused. The helper never recursively collects files.

Explain the selection, verification result, and any evidence limitations. A matching hash proves correspondence to this manifest, not authorship, authenticity, truth, or an independent timestamp. Manifest and files can be replaced together; use an external signature or independently retained root hash when authenticity matters. If a file changes during collection, retry only after the producer has finished.
