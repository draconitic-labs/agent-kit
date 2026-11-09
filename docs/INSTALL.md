# Install and remove

Run `python3 scripts/build.py` first. Install only one copy of a skill per harness to avoid duplicate names. Native marketplace installs and standalone copies are alternative routes. New sessions may be required to see changes.

## Claude Code

Register the generated marketplace root and install a package:

```bash
claude plugin marketplace add /path/to/agent-kit/dist/marketplace
claude plugin install draconitic-workbench@draconitic
claude plugin install draconitic-agents@draconitic
claude plugin install flintglade-products@draconitic
```

Choose just the package needed. Remove with `claude plugin uninstall draconitic-workbench@draconitic` (substitute the other package names). Manage the source with `claude plugin marketplace remove draconitic` after removing its plugins. For a temporary session, `claude --plugin-dir /path/to/generated/plugin` avoids a persistent marketplace installation.

## Codex

```bash
codex plugin marketplace add /path/to/agent-kit/dist/marketplace
codex plugin add draconitic-workbench@draconitic
codex plugin add draconitic-agents@draconitic
codex plugin add flintglade-products@draconitic
```

Remove a package with `codex plugin remove draconitic-workbench@draconitic`; remove its source with `codex plugin marketplace remove draconitic`. The generated `.agents/plugins/marketplace.json` is relative to the generated marketplace root. Workbench and Product Adapters declare local execution.

## Grok Build

```bash
grok plugin install /path/to/agent-kit/dist/marketplace/plugins/draconitic-workbench
grok plugin install /path/to/agent-kit/dist/marketplace/plugins/draconitic-agents
grok plugin install /path/to/agent-kit/dist/marketplace/plugins/flintglade-products
grok inspect --json
```

The current CLI prompts for trust; review the source before accepting. `grok plugin list` gives installed identifiers. Remove with `grok plugin uninstall <installed-identifier>`. Grok also understands Claude marketplace sources.

## ZCode

Settings → Plugins → Create → Add marketplace → select `dist/marketplace`. ZCode reads the Claude-compatible marketplace catalog and prefers each package's `.zcode-plugin/plugin.json`. Install and enable the chosen package, then inspect Settings → Skills and Plugin MCP servers. Skills are flat `skills/<name>/SKILL.md` folders. Disable or uninstall from Settings → Plugins.

## Gemini CLI

Each generated plugin directory is also an extension:

```bash
gemini extensions install /path/to/agent-kit/dist/marketplace/plugins/draconitic-workbench
gemini extensions list
```

For Agents or Products, substitute that package directory. Its individual plugin ZIP has `gemini-extension.json` at the archive root for release distribution. Remove with `gemini extensions uninstall draconitic-workbench`.

## Cursor, Copilot, OpenCode and Cline

Cursor can consume the generated `.cursor-plugin/marketplace.json` or a chosen package's `.cursor-plugin/plugin.json` through its Add from GitHub or local development workflow.

For portable standalone use, unzip a `*-skill.zip` into a folder named exactly as the skill. Put it under the selected harness's supported skills directory:

| Harness | Project directory |
| --- | --- |
| Codex / shared Agent Skills | `.agents/skills/<skill-name>/` |
| Claude Code | `.claude/skills/<skill-name>/` |
| ZCode | User directory `~/.zcode/skills/<skill-name>/` documented by ZCode |
| Grok Build | `.grok/skills/<skill-name>/` |
| Copilot | `.github/skills/<skill-name>/` |
| OpenCode | `.opencode/skills/<skill-name>/` |
| Cline | `.cline/skills/<skill-name>/` |

A standalone Public Evidence skill does not install an MCP connection. Configure `https://agents.draconitic.com/mcp` through that harness's MCP settings, or use the HTTP API described in the skill's `SKILL.md`, whose OpenAPI document is `https://agents.draconitic.com/openapi.json`. Delete only the specific copied skill directory to remove it. Do not overwrite an existing skill folder or replace an entire skills directory.
