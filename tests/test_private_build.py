"""A missing transitive reader dependency must preserve an existing Studio build."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("private_studio_build", ROOT / "studio-cf/build_dist.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PrivateBuildDependencies(unittest.TestCase):
    def test_missing_reader_package_preserves_previous_dist_before_valid_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "studio/data").mkdir(parents=True)
            (root / "site").mkdir()
            (root / "studio/data/review.json").write_text(json.dumps({"pages": []}))
            (root / "site/reader-features.js").write_text("import './reader-packages.js';\n")
            out = root / "studio-cf/dist"
            out.mkdir(parents=True)
            sentinel = out / "existing-output"
            sentinel.write_bytes(b"preserve previous assembled output")
            with patch.object(builder, "ROOT", root), patch.object(builder, "HERE", root / "studio-cf"):
                self.assertEqual(builder.main([]), 1)
                self.assertEqual(sentinel.read_bytes(), b"preserve previous assembled output")
                self.assertEqual([p.name for p in out.iterdir()], ["existing-output"])
                (root / "site/reader-packages.js").write_text("export const fixture = true;\n")
                self.assertEqual(builder.main([]), 0)
                for module in ("reader-features.js", "reader-packages.js"):
                    self.assertEqual((out / "site" / module).read_bytes(), (root / "site" / module).read_bytes())


if __name__ == "__main__":
    unittest.main()
