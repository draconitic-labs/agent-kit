---
name: flintglade-greenlit
description: Use the existing Greenlit Goods CLI to preflight Google Merchant Center feeds and make its supported conservative repairs. Use with an installed greenlit binary or a user-requested setup; not for Shopify catalog administration or promises of Merchant Center approval.
license: MIT
---

Requires: A separately installed Greenlit Goods greenlit executable. Product licensing is separate from this adapter.


Check `greenlit --help` and `greenlit audit --help` before choosing flags. The public product source is `https://github.com/flintglade-tools/greenlit-goods`; this adapter bundles no binary and does not silently install one.

Audit a user-supplied feed with `greenlit audit /path/to/feed.xml --json`. Use `--strict` for a requested CI gate: exit 0 means completed, exit 1 means red products or incomplete input under strict mode, and exit 2 means a command/input error. Keep the tool's `schema_version`, finding basis and dated normative sources in any derived report. Distinguish feed structure, specification findings and Greenlit heuristics.

If repair is requested, write a separate output with `greenlit fix /path/to/feed.xml --output /path/to/feed.fixed.xml`; never replace the source. Inspect the fix log and re-audit the new file. Supported repairs trim known scalar fields and normalize recognized enum/price forms. They do not invent identifiers, brands, currency or product facts. Unsupported XML structures must remain unmodified rather than being reconstructed speculatively.

Explain input coverage and retained unknowns. The tool does not inspect live landing pages, images, account status or Google policy enforcement. Revenue estimates are assumptions and currencies stay separate. Source and release licensing for Greenlit Goods remain those of the product, independent of this MIT adapter.
