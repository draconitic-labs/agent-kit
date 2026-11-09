# Security

Report vulnerabilities privately through [GitHub private vulnerability reporting](https://github.com/draconitic-labs/agent-kit/security/advisories/new), or at [support@draconitic.com](mailto:support@draconitic.com).

Fixes go to the `main` branch. There are no maintained older branches.

The Workbench helpers read only the files named on their command line and make no network requests. Evidence Pack refuses symlinks, paths outside the chosen root, common credential filenames and existing output paths. The builder refuses symlinked inputs and packages only the selected files. The Agents plugin connects to `https://agents.draconitic.com/mcp` and sends tool arguments there.
