#!/usr/bin/env python3
"""Build self-contained harness catalogs and deterministic plugin/skill ZIPs."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def archive(source, destination):
    if source.is_symlink():
        raise ValueError('archive root must not be a symlink')
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(source.rglob('*')):
            if path.is_symlink():
                raise ValueError('release cannot contain symlinks')
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            item = zipfile.ZipInfo(path.relative_to(source).as_posix(), (2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            z.writestr(item, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def owned_regular(path):
    """Refuse symlinked sources, including any ancestor inside this kit."""
    relative = path.relative_to(ROOT)
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('release inputs must not contain symlinks')
    if not path.is_file():
        raise ValueError('expected a regular release input')
    return path


def build():
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    version = catalog['version']
    dist = ROOT / 'dist'
    # This fixed generated path is the only tree the builder removes.
    if dist.is_symlink():
        raise ValueError('dist must not be a symlink')
    if dist.exists():
        shutil.rmtree(dist)
    market = dist / 'marketplace'
    market.mkdir(parents=True)
    claude_entries, openai_entries, cursor_entries = [], [], []
    for info in catalog['plugins']:
        name = info['name']
        source = ROOT / 'plugins' / name
        target = market / 'plugins' / name
        # copytree follows symlinks by default, so reject them first.
        if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
            raise ValueError('source plugins must contain regular files')
        for path in source.rglob('*'):
            if path.is_file(): owned_regular(path)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (target / 'assets').mkdir()
        shutil.copyfile(owned_regular(ROOT / 'assets' / 'draconitic-mark.svg'), target / 'assets' / 'icon.svg')
        shutil.copyfile(owned_regular(ROOT / 'LICENSE'), target / 'LICENSE')
        for doc in ('PRIVACY.md', 'TERMS.md'):
            shutil.copyfile(owned_regular(ROOT / 'docs' / doc), target / doc)
        metadata = {'name': name, 'version': version, 'description': info['description'],
                    'author': catalog['publisher'], 'homepage': 'https://draconitic.com', 'license': 'MIT'}
        interface = {'displayName': info['display_name'], 'shortDescription': info['short_description'],
                     'longDescription': (source / 'README.md').read_text(), 'developerName': 'Draconitic Labs',
                     'category': 'Developer Tools', 'websiteURL': 'https://draconitic.com',
                     'composerIcon': './assets/icon.svg', 'logo': './assets/icon.svg', 'capabilities': []}
        overlay = {'interface': interface, 'requires_local_executor': info['local_executor']}
        portable = {'$schema': SCHEMA + 'plugin.schema.json', **metadata,
                    'extensions': {'com.openai': overlay}}
        write_json(target / 'plugin.json', portable)
        compat = dict(metadata)
        if info.get('mcp_url'):
            write_json(target / 'mcp.json', {'$schema': SCHEMA + 'mcp.schema.json',
                       'mcpServers': {'draconitic': {'type': 'streamable-http', 'url': info['mcp_url']}}})
            write_json(target / '.mcp.json', {'mcpServers': {'draconitic': {'type': 'http', 'url': info['mcp_url']}}})
            compat['mcpServers'] = './.mcp.json'
        write_json(target / '.claude-plugin' / 'plugin.json', {**compat, 'icon': './assets/icon.svg'})
        write_json(target / '.zcode-plugin' / 'plugin.json', compat)
        write_json(target / '.cursor-plugin' / 'plugin.json', {**compat, 'logo': './assets/icon.svg'})
        write_json(target / '.codex-plugin' / 'plugin.json', {**compat, 'skills': './skills/', **overlay})
        write_json(target / 'gemini-extension.json', {'name': name, 'version': version,
                   'description': info['description'], **({'mcpServers': {'draconitic': {'httpUrl': info['mcp_url']}}} if info.get('mcp_url') else {})})
        claude_entries.append({'name': name, 'source': './plugins/' + name, 'version': version, 'description': info['description']})
        openai_entries.append({'name': name, 'source': {'source': 'local', 'path': './plugins/' + name},
                               'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Developer Tools'})
        cursor_entries.append({'name': name, 'source': './plugins/' + name})
        for skill in sorted((target / 'skills').iterdir()):
            if not skill.is_dir(): continue
            shutil.copyfile(owned_regular(ROOT / 'LICENSE'), skill / 'LICENSE')
            archive(skill, dist / (skill.name + '-' + version + '-skill.zip'))
        archive(target, dist / (name + '-' + version + '.zip'))
    write_json(market / '.claude-plugin' / 'marketplace.json', {'name': 'draconitic', 'owner': catalog['publisher'], 'description': 'Draconitic evidence tools and Flintglade product adapters for coding agents.', 'plugins': claude_entries})
    write_json(market / '.agents' / 'plugins' / 'marketplace.json', {'name': 'draconitic', 'interface': {'displayName': 'Draconitic Labs'}, 'plugins': openai_entries})
    write_json(market / '.cursor-plugin' / 'marketplace.json', {'name': 'draconitic', 'owner': catalog['publisher'], 'plugins': cursor_entries})
    archive(market, dist / ('draconitic-marketplace-' + version + '.zip'))
    sums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in sorted(dist.glob('*.zip')))
    (dist / 'SHA256SUMS').write_text(sums)
    return {'version': version, 'plugins': len(catalog['plugins']), 'archives': len(list(dist.glob('*.zip')))}


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
