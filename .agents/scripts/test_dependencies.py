"""Dependency setup must reject aliases before invoking any installer."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import dependencies


class DependencyPathTests(unittest.TestCase):
    def test_hardlinked_binary_cannot_overwrite_unrelated_file(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            tools = base / 'tools'
            (tools / 'bin').mkdir(parents=True)
            peer = base / 'other-application'
            peer.write_bytes(b'preserve unrelated application')
            binary = tools / 'bin' / ('ast-grep.exe' if os.name == 'nt' else 'ast-grep')
            os.link(peer, binary)
            with patch.object(dependencies.shutil, 'which', return_value=sys.executable), \
                 patch.object(dependencies, 'npm_command', return_value=[sys.executable]), \
                 patch.object(dependencies, 'run') as install:
                with self.assertRaisesRegex(ValueError, 'unaliased'):
                    dependencies.provision(tools)
                install.assert_not_called()
            self.assertEqual(peer.read_bytes(), b'preserve unrelated application')

    def test_reparse_or_symlink_bin_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            tools = base / 'tools'
            tools.mkdir()
            other = base / 'other'
            other.mkdir()
            try:
                (tools / 'bin').symlink_to(other, target_is_directory=True)
            except OSError:
                self.skipTest('Host does not permit test directory symlinks')
            with patch.object(dependencies.shutil, 'which', return_value=sys.executable), \
                 patch.object(dependencies, 'npm_command', return_value=[sys.executable]), \
                 patch.object(dependencies, 'run') as install:
                with self.assertRaisesRegex(ValueError, 'links/reparse'):
                    dependencies.provision(tools)
                install.assert_not_called()
            self.assertFalse(list(other.iterdir()))


if __name__ == '__main__':
    unittest.main()
