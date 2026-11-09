# Draconitic Workbench

Three local tools for agents: explicit-file evidence bundles, extension manifest review and typed JSON snapshot comparison. Python 3.10+; standard library only. Scripts run only when the agent invokes them. They do not make network requests, install hooks or change harness permissions.

Each skill is self-contained. Read its `SKILL.md` for commands and limits. The manifest reviewer provides declaration cues, not a complete security verdict; hashes are integrity evidence, not proof of truth; snapshot arrays compare by index.

Local files can contain personal data. Review selected inputs and generated reports before sharing. Files remain on the computer unless the host agent or user uploads them. The host model's own data policy still applies. See `PRIVACY.md` and `TERMS.md`.

Support: support@draconitic.com · https://draconitic.com
