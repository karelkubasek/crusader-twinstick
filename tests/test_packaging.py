# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_portable


class PackagingTests(unittest.TestCase):
    def test_generated_tools_game_files_and_saves_are_ignored_by_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", root], check=True)
            (root / ".gitignore").write_bytes((build_portable.ROOT / ".gitignore").read_bytes())
            paths = ["runtime-tools/bin/innoextract", "runtime-engine/bin/scummvm", "runtime/lib/libSDL3.so.0",
                     "user-data/installation/game-data/STATIC/SHAPES.FLX", "dist/player.tar.gz",
                     "setup_crusader.EXE", "personal/player.001", "game-files/GAME.GOG"]
            result = subprocess.run(["git", "check-ignore", "--stdin", "--no-index"], cwd=root,
                                    input="\n".join(paths) + "\n", capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.splitlines(), paths)

    def test_engine_patch_export_works_inside_parent_git_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", root], check=True)
            engine = root / "build/exported-engine"
            expected = root / "expected"
            engine.mkdir(parents=True)
            expected.mkdir()
            (engine / "file.txt").write_text("old\n")
            (expected / "file.txt").write_text("new\n")
            patch_file = root / "change.patch"
            patch_file.write_text("diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old\n+new\n")
            build_portable.apply_engine_patch(engine, expected, patch_file)
            self.assertEqual((engine / "file.txt").read_text(), "new\n")

    def test_loader_paths_cannot_escape_library_destination(self):
        output = "  libSDL2.so.0 => /usr/lib/libSDL2.so.0 (0x123)\n  /home/linuxbrew/lib/ld.so => /usr/lib/ld-linux-x86-64.so.2 (0x456)"
        with patch.object(build_portable, "run", return_value=output):
            self.assertEqual(build_portable.dependencies(Path("engine")), [("libSDL2.so.0", Path("/usr/lib/libSDL2.so.0"))])

    def test_unrecognized_absolute_dependency_is_rejected(self):
        with patch.object(build_portable, "run", return_value=" /outside/library.so => /usr/lib/library.so (0x1)"):
            with self.assertRaisesRegex(RuntimeError, "absolute library"):
                build_portable.dependencies(Path("engine"))

    def test_distribution_allowlist_excludes_game_data_and_local_state(self):
        files = list(build_portable.source_files())
        self.assertTrue(files)
        for path in files:
            relative = path.relative_to(build_portable.ROOT)
            self.assertNotIn(relative.parts[0], ("user-data", "runtime", "runtime-engine", "dist", "vendor", "installers"))
            self.assertNotIn(path.suffix.lower(), (".exe", ".gog", ".flx", ".avi", ".ico", ".png", ".pdf"))


if __name__ == "__main__":
    unittest.main()
