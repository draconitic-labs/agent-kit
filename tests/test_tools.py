import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'plugins/draconitic-workbench/skills'


def module(skill, filename):
    spec = importlib.util.spec_from_file_location(filename, SKILLS / skill / 'scripts' / (filename + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


evidence = module('draconitic-evidence-pack', 'evidence')
manifest = module('draconitic-manifest-review', 'manifest_review')
snapshot = module('draconitic-snapshot-diff', 'snapshot_diff')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'input'; self.root.mkdir()
        (self.root / 'report.txt').write_text('Synthetic public result\n')
        self.out = Path(self.temp.name) / 'bundle'

    def create(self, files=None):
        return evidence.create(self.root, files or ['report.txt'], self.out, ['https://example.org/source'])

    def test_round_trip_is_portable_and_unchanged(self):
        original = (self.root / 'report.txt').read_bytes()
        result = self.create(); checked = evidence.verify(self.out)
        self.assertEqual(result['manifest_sha256'], checked['manifest_sha256'])
        self.assertEqual((self.root / 'report.txt').read_bytes(), original)
        self.assertNotIn(str(self.root), (self.out / 'manifest.json').read_text())

    def test_reproducible_manifest(self):
        result = self.create(); self.out = self.out.with_name('second')
        self.assertEqual(result['manifest_sha256'], self.create()['manifest_sha256'])

    def test_no_clobber(self):
        self.out.mkdir(); (self.out / 'keep').write_text('keep')
        with self.assertRaises(ValueError): self.create()
        self.assertEqual((self.out / 'keep').read_text(), 'keep')

    def test_tampering_detected(self):
        self.create(); (self.out / 'files/report.txt').write_text('changed')
        with self.assertRaises(ValueError): evidence.verify(self.out)

    def test_unexpected_files_detected(self):
        self.create(); (self.out / 'extra.txt').write_text('extra')
        with self.assertRaises(ValueError): evidence.verify(self.out)

    def test_path_escape_refused_and_partial_output_removed(self):
        for name in ['../escape.txt', '/etc/hosts', 'a/../report.txt', 'a\\report.txt', 'C:/report.txt']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError): self.create([name])
                self.assertFalse(self.out.exists())

    def test_symlink_and_symlink_directory_refused(self):
        (self.root / 'link').symlink_to(self.root / 'report.txt')
        (self.root / 'dir').symlink_to(self.root, target_is_directory=True)
        for name in ['link', 'dir/report.txt']:
            with self.assertRaises(ValueError): self.create([name])

    def test_secret_filename_refused(self):
        for name in ['.env', 'x.pem', '.env.production', 'key.secret']:
            (self.root / name).write_text('synthetic fixture')
            with self.assertRaises(ValueError): self.create([name])

    def test_more_credential_paths_refused(self):
        for name in ['id_ecdsa', 'id_dsa', '.git-credentials', '.pgpass', '.kube/config',
                     '.docker/config.json', '.config/gh/hosts.yml', 'home/.config/gh/config.yml']:
            with self.subTest(name=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic fixture')
                with self.assertRaises(ValueError): self.create([name])
                self.assertFalse(self.out.exists())

    def test_duplicate_selection_refused(self):
        with self.assertRaises(ValueError): self.create(['report.txt', 'report.txt'])

    def test_manifest_traversal_refused(self):
        self.create(); p = self.out / 'manifest.json'; data = json.loads(p.read_text())
        data['files'][0]['path'] = '../../input/report.txt'; p.write_text(json.dumps(data))
        with self.assertRaises(ValueError): evidence.verify(self.out)

    def test_symlink_in_bundle_refused(self):
        self.create(); (self.out / 'unexpected').symlink_to(self.root)
        with self.assertRaises(ValueError): evidence.verify(self.out)

    @unittest.skipIf(sys.platform == 'win32', 'POSIX permission test')
    def test_unreadable_extra_directory_cannot_pass(self):
        self.create(); hidden = self.out / 'extra'; hidden.mkdir()
        (hidden / 'unlisted.txt').write_text('unexpected'); hidden.chmod(0)
        try:
            with self.assertRaises((ValueError, OSError)): evidence.verify(self.out)
        finally: hidden.chmod(0o700)

    def test_source_credentials_and_queries_refused(self):
        for url in ['https://user:pass@example.org', 'https://example.org?token=synthetic', 'file:///etc/hosts']:
            with self.assertRaises(ValueError): evidence.create(self.root, ['report.txt'], self.out, [url])

    def test_file_limit_enforced_without_large_fixture(self):
        old = evidence.MAX_FILE; evidence.MAX_FILE = 2
        try:
            with self.assertRaises(ValueError): self.create()
        finally: evidence.MAX_FILE = old


class ManifestTests(unittest.TestCase):
    def test_required_optional_and_content_scopes_are_distinct(self):
        result = manifest.review({'manifest_version': 3, 'permissions': ['storage'], 'optional_permissions': ['cookies'],
            'host_permissions': ['https://example.org/*'], 'optional_host_permissions': ['<all_urls>'],
            'content_scripts': [{'matches': ['https://*/*'], 'exclude_matches': ['https://example.org/*']}]})
        cues = result['review_cues']
        self.assertTrue(any(x['field'] == 'optional_permissions' and x['value'] == 'cookies' for x in cues))
        self.assertTrue(any(x['field'] == 'optional_host_permissions' for x in cues))
        self.assertEqual(result['content_script_scope'][0]['exclude_matches'], ['https://example.org/*'])

    def test_delta_keeps_removed_and_added(self):
        result = manifest.review({'manifest_version': 3, 'permissions': ['cookies']},
                                 {'manifest_version': 3, 'permissions': ['storage']})
        self.assertEqual(result['baseline_delta']['permissions'], {'added': ['cookies'], 'removed': ['storage']})

    def test_removed_content_exclusion_is_a_reported_change(self):
        old = {'manifest_version': 3, 'content_scripts': [{'matches': ['https://*/*'], 'exclude_matches': ['https://private.example/*']}]}
        new = {'manifest_version': 3, 'content_scripts': [{'matches': ['https://*/*']}]}
        result = manifest.review(new, old)
        self.assertEqual(result['baseline_delta']['content_scripts']['before'], old['content_scripts'])
        self.assertEqual(result['baseline_delta']['content_scripts']['after'], new['content_scripts'])

    def test_mv2_host_entries(self):
        result = manifest.review({'manifest_version': 2, 'permissions': ['<all_urls>']})
        self.assertEqual(result['review_cues'][0]['code'], 'broad-host-access')

    def test_bad_types_fail(self):
        for data in [[], {}, {'manifest_version': True}, {'manifest_version': 3, 'permissions': 'cookies'},
                     {'manifest_version': 3, 'content_scripts': [None]}, {'manifest_version': 3, 'content_security_policy': []}]:
            with self.subTest(data=data):
                with self.assertRaises(ValueError): manifest.review(data)


class SnapshotTests(unittest.TestCase):
    def test_null_and_missing(self):
        result = snapshot.diff({}, {'a': None})
        self.assertEqual(result['changes'], [{'kind': 'added', 'path': '/a', 'after': {'type': 'null', 'value': None}}])

    def test_boolean_is_not_integer(self):
        self.assertEqual(snapshot.diff(True, 1)['total_changes'], 1)

    def test_json_pointer_escaping(self):
        self.assertEqual(snapshot.diff({'a/b~c': 1}, {'a/b~c': 2})['changes'][0]['path'], '/a~1b~0c')

    def test_truncation_keeps_total(self):
        result = snapshot.diff([1, 2, 3], [3, 4, 5], 1)
        self.assertEqual(result['total_changes'], 3); self.assertTrue(result['truncated'])
        self.assertEqual(len(result['changes']), 1)

    def test_large_decimals_exact(self):
        result = snapshot.diff(Decimal('1.00000000000000000001'), Decimal('1.00000000000000000002'))
        self.assertEqual(result['total_changes'], 1)
        self.assertEqual(result['changes'][0]['after'], {'type': 'decimal', 'value': '1.00000000000000000002'})

    def test_decimal_cannot_collide_with_user_object(self):
        result = snapshot.diff(Decimal('1.5'), {'type': 'decimal', 'value': '1.5'})
        change = result['changes'][0]
        self.assertNotEqual(change['before'], change['after'])
        self.assertEqual(change['after']['type'], 'object')

    def test_equal_decimal_values_ignore_lexical_zeroes(self):
        self.assertEqual(snapshot.diff(Decimal('1.00'), Decimal('1.0'))['total_changes'], 0)

    def test_duplicate_keys_and_nonfinite_and_depth_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'snapshot.json'
            for content in ['{"a":1,"a":2}', '[NaN]', '[Infinity]', '[' * 130 + '0' + ']' * 130]:
                p.write_text(content)
                with self.assertRaises((ValueError, RecursionError)): snapshot.load(p)

    def test_cli_exit_codes_and_input_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            before, after = Path(temp) / 'before.json', Path(temp) / 'after.json'
            before.write_text('{"a":1}'); after.write_text('{"a":2}')
            script = SKILLS / 'draconitic-snapshot-diff/scripts/snapshot_diff.py'
            cmd = [sys.executable, str(script), str(before), str(after), '--check']
            run = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1); self.assertEqual(json.loads(run.stdout)['total_changes'], 1)
            self.assertEqual(before.read_text(), '{"a":1}')
            after.write_text(before.read_text()); self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            after.write_text('invalid'); self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)


if __name__ == '__main__': unittest.main()
