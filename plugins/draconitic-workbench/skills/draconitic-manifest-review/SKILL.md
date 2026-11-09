---
name: draconitic-manifest-review
description: Review declared Chrome or Firefox extension permissions, broad host access, and permission changes from local manifest.json files. Use before shipping or reviewing an extension manifest; not as a complete extension security audit or store-approval predictor.
license: MIT
---

Requires: Python 3.10 or newer and local file execution.


Run `scripts/manifest_review.py` relative to this skill's installed directory:

```bash
python3 scripts/manifest_review.py /path/to/manifest.json
python3 scripts/manifest_review.py /path/to/new/manifest.json --baseline /path/to/old/manifest.json
```

The helper reads declared required and optional permissions, MV2 permission-host entries, MV3 host permissions, content-script matches and exclusion/narrowing declarations. It reports review cues and the precise added/removed permission sets. Optional capabilities are requests that require a later grant, not proof of current access. Host patterns are compared literally; equivalent or overlapping patterns are not collapsed. Read the matching extension code before interpreting a cue as necessary or unsafe.

Use the result to explain what a user would grant, which new declarations need justification, and where runtime review is still needed. The helper never rewrites the manifest and does not fetch sites or extension source. Exit 0 means review completed even when cues exist; exit 2 means invalid input. No findings does not establish security, platform compatibility, or store acceptance. For current store requirements, consult the platform's official documentation when making submission claims.
