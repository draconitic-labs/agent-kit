# Draconitic Agent Kit

Draconitic Agent Kit is a set of plugins and portable skills for coding agents: three local evidence tools, a connection to the public Draconitic Agents evidence service, and adapters for two Flintglade products. One source tree builds packages for Claude Code, Codex, Grok Build, ZCode, Cursor and Gemini CLI, plus standalone skill archives for any harness that reads Agent Skills.

| Package | Skills | What runs |
| --- | --- | --- |
| Draconitic Workbench | Evidence Pack, Manifest Review, Snapshot Diff | Three Python helpers that read only the files you name; standard library only |
| Draconitic Agents | Public Evidence | The public MCP service at `https://agents.draconitic.com/mcp`, with six read tools |
| Flintglade Product Adapters | Greenlit Goods, Proscenium | Separately installed [Greenlit Goods](https://github.com/flintglade-tools/greenlit-goods) and [Proscenium](https://github.com/flintglade-tools/proscenium) binaries, under their own licenses |

## Skills

- **Evidence Pack** copies an explicit list of files into a bundle with a SHA-256 manifest, and verifies a bundle later. It refuses symlinks, paths outside the root, common credential filenames and existing output paths.
- **Manifest Review** reads a browser-extension manifest and reports required and optional permissions, broad host patterns, and the changes against a baseline manifest, including content scripts, CSP, externally connectable and web-accessible resources.
- **Snapshot Diff** compares two JSON documents value by value, keeping types exact (boolean vs integer, null vs missing, exact decimals), and reports each change at its JSON Pointer.
- **Public Evidence** searches the Draconitic Agents corpus of dated public records, lists datasets, checks exact package identifiers, lists revisions since a date, and checks citation membership and claim spans against returned records.
- **Greenlit Goods** runs `greenlit audit` on a Google Merchant Center feed and writes `greenlit fix` repairs to a new file.
- **Proscenium** builds and runs deterministic webhook scenarios against a receiver on the local machine.

## Build

Python 3.10 or newer:

```bash
python3 scripts/build.py
python3 -m unittest discover -s tests -v
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/validate.py
```

`scripts/build.py` writes `dist/`: one ZIP per plugin, one ZIP per skill, a marketplace ZIP, the marketplace tree in `dist/marketplace`, and `SHA256SUMS`. Rebuilding with the same Python and zlib versions gives byte-identical archives. The builder removes and recreates `dist/` on every run, so keep nothing else there.

`scripts/validate.py` checks every generated manifest, skill header and archive. `--schema-dir DIR` also validates the manifests against the Agent Plugins schemas; download https://agent-plugins.org/schemas/1.0.0/plugin.schema.json and https://agent-plugins.org/schemas/1.0.0/mcp.schema.json into `DIR` as `plugin-schema.json` and `mcp-schema.json`. `scripts/check_native.py [receipt.json]` validates and installs the packages with whichever of `claude`, `codex` and `grok` are installed, using throwaway configuration directories; it runs no model. `scripts/smoke_remote.py` calls every read tool of the public Agents service once.

`integrations/mcp-registry/server.json` describes the Agents service for the [MCP Registry](https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json), as a remote streamable-HTTP server.

## Install

See [docs/INSTALL.md](docs/INSTALL.md). For Claude Code:

```bash
claude plugin marketplace add /path/to/agent-kit/dist/marketplace
claude plugin install draconitic-workbench@draconitic
```

## Data handling

The Workbench helpers make no network requests. The Agents plugin sends tool arguments to `agents.draconitic.com`. See [docs/PRIVACY.md](docs/PRIVACY.md) and [docs/TERMS.md](docs/TERMS.md).

## License

MIT. See [LICENSE](LICENSE). Greenlit Goods and Proscenium are separate products with their own licenses.
