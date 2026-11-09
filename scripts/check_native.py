#!/usr/bin/env python3
"""Check installed harnesses using disposable configuration directories, no models.

Usage: check_native.py [receipt.json]
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OWN_PREFIXES = ('draconitic-', 'flintglade-')


def check():
    market = ROOT / 'dist/marketplace'
    records = []
    with tempfile.TemporaryDirectory(prefix='draconitic-check-') as temp:
        env = os.environ.copy()
        for var, name in [('CLAUDE_CONFIG_DIR', 'claude'), ('GROK_HOME', 'grok'), ('CODEX_HOME', 'codex')]:
            path = Path(temp) / name; path.mkdir(); env[var] = str(path)

        def run(command):
            result = subprocess.run(command, env=env, cwd=market, text=True, capture_output=True, timeout=60)
            output = (result.stdout + result.stderr).replace(str(ROOT), '<KIT>').replace(temp, '<ISOLATED>')
            row = {'command': [x.replace(str(ROOT), '<KIT>') for x in command], 'exit_code': result.returncode, 'output': output}
            records.append(row)

        if shutil.which('claude'):
            run(['claude', 'plugin', 'validate', str(market), '--strict', '--json'])
            for plugin in sorted((market / 'plugins').iterdir()):
                run(['claude', 'plugin', 'validate', str(plugin), '--strict', '--profile', 'directory', '--json'])
        if shutil.which('grok'):
            for plugin in sorted((market / 'plugins').iterdir()):
                run(['grok', 'plugin', 'validate', str(plugin)])
                run(['grok', 'plugin', 'install', str(plugin), '--trust'])
                run(['grok', 'plugin', 'details', plugin.name])
            result = subprocess.run(['grok', 'inspect', '--json'], env=env, cwd=market,
                                    text=True, capture_output=True, timeout=60)
            if result.returncode:
                raise RuntimeError('grok discovery failed')
            discovered = json.loads(result.stdout)
            # Grok also reads existing Claude compatibility roots. Retain only
            # this kit's inventory; never publish the user's unrelated settings.
            own = {'skills': [x['name'] for x in discovered.get('skills', []) if x.get('name', '').startswith(OWN_PREFIXES)],
                   'plugins': [{'name': x['name'], 'enabled': x.get('enabled'), 'provides': x.get('provides')}
                               for x in discovered.get('plugins', []) if x.get('name', '').startswith(OWN_PREFIXES)],
                   'mcp': [{'name': x['name'], 'target': x.get('target'), 'transport': x.get('transport')}
                           for x in discovered.get('mcpServers', []) if x.get('name') == 'draconitic']}
            if len(own['skills']) != 6 or len(own['plugins']) != 3 or len(own['mcp']) != 1:
                raise RuntimeError('Grok did not discover the complete kit')
            records.append({'command': ['grok', 'inspect', '--json', '(kit inventory only)'], 'exit_code': 0,
                            'output': json.dumps(own, indent=2)})
        if shutil.which('codex'):
            run(['codex', 'plugin', 'marketplace', 'add', str(market)])
            run(['codex', 'plugin', 'list', '--json'])
            for plugin in sorted((market / 'plugins').iterdir()):
                run(['codex', 'plugin', 'add', plugin.name + '@draconitic', '--json'])
        for tool in ['claude', 'grok', 'codex']:
            if shutil.which(tool): run([tool, '--version'])
    return records


if __name__ == '__main__':
    records = check()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(records, indent=2) + '\n')
    for row in records:
        print(row['exit_code'], ' '.join(row['command']))
        if row['exit_code']: print(row['output'][:2000])
    raise SystemExit(int(any(r['exit_code'] for r in records)))
