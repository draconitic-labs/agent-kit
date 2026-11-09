#!/usr/bin/env python3
"""Inspect extension manifest declarations without changing or executing them."""
import argparse
import json
from pathlib import Path
import sys

REVIEW = {
    'debugger': 'Can inspect and control debug targets; justify the target scope.',
    'nativeMessaging': 'Can communicate with installed native applications.',
    'cookies': 'Can access cookies for granted hosts; inspect handling and retention.',
    'management': 'Can inspect or manage other installed extensions.',
    'history': 'Can access browsing history.',
    'clipboardRead': 'Can read clipboard contents when permitted by the platform.',
    'webRequestBlocking': 'Can synchronously affect requests in supported environments.',
    'downloads': 'Can initiate and manage downloads.',
    'proxy': 'Can change browser proxy configuration.',
}
FIELDS = ('permissions', 'optional_permissions', 'host_permissions', 'optional_host_permissions')


def strings(value, field):
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError(field + ' must be an array of strings')
    return sorted(set(value))


def load(path):
    with Path(path).open('rb') as f:
        data = f.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('manifest exceeds 1 MiB')
    return json.loads(data)


def declarations(manifest):
    if not isinstance(manifest, dict) or type(manifest.get('manifest_version')) is not int or manifest['manifest_version'] not in (2, 3):
        raise ValueError('expected a manifest_version 2 or 3 object')
    sets = {field: strings(manifest.get(field, []), field) for field in FIELDS}
    scripts = manifest.get('content_scripts', [])
    if not isinstance(scripts, list) or any(not isinstance(x, dict) for x in scripts):
        raise ValueError('content_scripts must be an array of objects')
    sets['content_script_matches'] = sorted({p for s in scripts for p in strings(s.get('matches', []), 'matches')})
    return sets


def review(manifest, baseline=None):
    sets = declarations(manifest)
    cues = []
    for field in ('permissions', 'optional_permissions'):
        for permission in sets[field]:
            if permission in REVIEW:
                cues.append({'code': 'sensitive-capability', 'field': field, 'value': permission, 'reason': REVIEW[permission]})
    for field, patterns in sets.items():
        for pattern in patterns:
            if pattern in ('<all_urls>', '*://*/*', 'http://*/*', 'https://*/*', 'file:///*'):
                cues.append({'code': 'broad-host-access', 'field': field, 'value': pattern,
                             'reason': 'Review whether this host scope is needed and when access is granted.'})
    csp = manifest.get('content_security_policy')
    if csp is not None and not isinstance(csp, (str, dict)):
        raise ValueError('content_security_policy must be a string or object')
    if csp is not None:
        cues.append({'code': 'csp-manual-review', 'field': 'content_security_policy', 'value': csp,
                     'reason': 'Inspect policy directives and referenced resources; this helper does not parse CSP.'})
    content_scope = []
    for script in manifest.get('content_scripts', []):
        content_scope.append({key: strings(script[key], key) for key in
                              ('matches', 'exclude_matches', 'include_globs', 'exclude_globs') if key in script})
    delta = None
    if baseline is not None:
        old = declarations(baseline)
        delta = {field: {'added': sorted(set(sets[field]) - set(old[field])),
                         'removed': sorted(set(old[field]) - set(sets[field]))} for field in sets}
        # Whole script records retain associations, excludes, globs, worlds and
        # execution timing. Flattened host sets alone hide access expansions.
        previous_scripts = baseline.get('content_scripts', [])
        if previous_scripts != manifest.get('content_scripts', []):
            delta['content_scripts'] = {'before': previous_scripts, 'after': manifest.get('content_scripts', [])}
        for field in ('content_security_policy', 'externally_connectable', 'web_accessible_resources'):
            if baseline.get(field) != manifest.get(field):
                delta[field] = {'before': baseline.get(field), 'after': manifest.get(field)}
    return {'schema_version': 1, 'manifest_version': manifest['manifest_version'], 'declarations': sets,
            'content_script_scope': content_scope, 'baseline_delta': delta, 'review_cues': cues,
            'coverage': 'Declaration review only; no runtime, remote-code, data-flow or store-policy verdict.'}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('manifest'); p.add_argument('--baseline')
    a = p.parse_args()
    try:
        print(json.dumps(review(load(a.manifest), load(a.baseline) if a.baseline else None), indent=2)); return 0
    except (OSError, ValueError, TypeError) as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
