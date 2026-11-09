---
name: flintglade-proscenium
description: Prepare and run deterministic webhook receiver scenarios using an existing Proscenium installation. Use for local receiver signatures, duplicate-event behavior, expiry and failure evidence; not to send webhooks to production or bypass Pro features.
license: MIT
---

Requires: A separately installed Proscenium executable. Headless scenario runs require its Pro entitlement.


Check `proscenium --help` and `proscenium run --help` for the installed version. The public product repository is `https://github.com/flintglade-tools/proscenium`; the adapter includes no product code or entitlement. An unavailable binary or license is a setup dependency, not a passed test.

Use a receiver owned by the user on literal loopback or pinned localhost. Running a scenario sends requests to that receiver; use synthetic payloads. Read the installed product's scenario-format guide before constructing nontrivial packs. The core schema is version 1 with `name`, `description`, `endpoints`, and ordered `cases`; each case can specify `name`, `method`, `path`, `body`, `expected_status`, `expected_body_contains`, timing limits and `signature`. Unknown fields fail parsing.

Signature profiles are `generic_hmac_sha256`, `github_sha256`, `stripe_style`, and `standard_webhooks`. Put the name of an existing environment variable in `signature.secret_env`, never its value in a pack or command. Let the user or secret manager supply license/signing variables; never print them. Standard Webhooks uses the product's documented `whsec_` base64 format.

Repeat a synthetic event ID to test the receiver's idempotency contract; use a negative timestamp offset for expiry and `corrupt: true` for invalid signatures. Specify the receiver's real expected behavior rather than asserting that every receiver should return the same status for duplicates.

```bash
proscenium run --pack /path/to/scenarios.json --base-url http://127.0.0.1:3000/ --junit /path/to/new-artifacts/proscenium.xml
```

Exit 0 means all assertions passed, exit 1 means assertions failed, and exit 2 means invalid input or an operational error. Preserve failures and report the actual scenario and product version. A passing synthetic replay is evidence about that receiver and pack, not proof of production reliability or provider certification.
