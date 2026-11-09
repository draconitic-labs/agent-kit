import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('kit_builder', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)


class ReleaseInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'kit'; self.root.mkdir()
        for name in ['plugins', 'assets', 'docs']:
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ['catalog.json', 'LICENSE']:
            shutil.copyfile(ROOT / name, self.root / name)
        self.previous = builder.ROOT; builder.ROOT = self.root
        self.addCleanup(setattr, builder, 'ROOT', self.previous)
        self.outside = Path(self.temp.name) / 'outside.txt'; self.outside.write_text('Synthetic private fixture')

    def test_selected_asset_symlink_is_refused(self):
        p = self.root / 'assets/draconitic-mark.svg'; p.unlink(); p.symlink_to(self.outside)
        with self.assertRaises(ValueError): builder.build()

    def test_unselected_asset_is_not_packaged(self):
        (self.root / 'assets/unselected.txt').symlink_to(self.outside)
        builder.build()
        self.assertFalse(any((self.root / 'dist/marketplace').rglob('unselected.txt')))

    def test_document_and_license_symlinks_are_refused(self):
        for name in ['docs/PRIVACY.md', 'LICENSE']:
            p = self.root / name; data = p.read_bytes(); p.unlink(); p.symlink_to(self.outside)
            try:
                with self.assertRaises(ValueError): builder.build()
            finally:
                p.unlink(); p.write_bytes(data)

    def test_plugin_root_symlink_is_refused(self):
        p = self.root / 'plugins/draconitic-workbench'; renamed = self.root / 'moved-plugin'
        p.rename(renamed); p.symlink_to(renamed, target_is_directory=True)
        with self.assertRaises(ValueError): builder.build()


if __name__ == '__main__': unittest.main()
