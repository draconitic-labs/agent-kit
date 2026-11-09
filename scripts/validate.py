#!/usr/bin/env python3
"""Validate generated archives, skills and optional downloaded official schemas."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate(schema_dir=None):
    dist = ROOT / 'dist'; market = dist / 'marketplace'; skills, plugins, archives = 0, 0, 0
    for plugin in sorted((market / 'plugins').iterdir()):
        portable = json.loads((plugin / 'plugin.json').read_text()); plugins += 1
        for path in plugin.rglob('*'):
            if path.is_symlink(): raise ValueError('symlink in generated package')
        for host in ['.claude-plugin', '.zcode-plugin', '.codex-plugin', '.cursor-plugin']:
            compatibility = json.loads((plugin / host / 'plugin.json').read_text())
            for key in ('name', 'version', 'description', 'author', 'license'):
                assert portable[key] == compatibility[key], (plugin.name, host, key)
        interface = portable['extensions']['com.openai']['interface']
        assert 0 < len(interface['shortDescription']) <= 30
        assert 0 < len(interface['displayName']) <= 30
        assert len(interface['longDescription']) <= 4000
        for key in ('logo', 'composerIcon'):
            assert (plugin / interface[key]).is_file()
        for skill in (plugin / 'skills').iterdir():
            content = (skill / 'SKILL.md').read_text(); parts = content.split('---', 2)
            header = yaml.safe_load(parts[1]); name = header['name']; skills += 1
            assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) and len(name) <= 64
            assert name == skill.name and 0 < len(header['description']) <= 1024
            assert (skill / 'LICENSE').is_file()
            assert not any(x in content for x in ['<KIT>', 'TODO', '/home/', '/run/media/'])
        if schema_dir:
            import jsonschema
            for file, schema in [('plugin.json', 'plugin-schema.json'), ('mcp.json', 'mcp-schema.json')]:
                if (plugin / file).exists():
                    jsonschema.Draft202012Validator(json.loads((schema_dir / schema).read_text())).validate(json.loads((plugin / file).read_text()))
    expected_sums = {}
    for line in (dist / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1); expected_sums[name] = digest
    assert set(expected_sums) == {p.name for p in dist.glob('*.zip')}
    for path in dist.glob('*.zip'):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sums[path.name]
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            for name in z.namelist():
                assert not name.startswith('/') and '..' not in Path(name).parts
                assert '__pycache__' not in name and not name.endswith('.pyc')
                data = z.read(name)
                if name.endswith(('.py', '.md', '.json', '.yaml')):
                    assert b'/home/' not in data and b'/run/media/' not in data
        archives += 1
    return {'plugins': plugins, 'skills': skills, 'archives': archives, 'official_schemas': bool(schema_dir)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--schema-dir', type=Path); a = p.parse_args()
    print(json.dumps(validate(a.schema_dir), indent=2))
