"""Public navigation metadata must not enumerate withheld pages or blocks."""
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_public import filter_reader_metadata


class MetadataFiltering(unittest.TestCase):
    pages = [{"id": "page-a", "B": [{}, {}]}, {"id": "page-b", "B": [{}]},
             {"id": "page-hidden", "B": [{}]}]
    html = '''const PAL = [
      {id:"comparison",witnesses:[[["page-a",[0]]],[["page-a",[1]]],[["page-hidden","all"]]]},
      {id:"whole",witnesses:[[["page-a","all"]],[["page-b","all"]]]}
    ];
    const HF = ["page-a","page-hidden"];'''

    def parse(self, value, name):
        return json.loads(re.search(r"const " + name + r" = (.*?);", value, re.S).group(1))

    def test_exact_selected_blocks_drop_hidden_witness_and_empty_comparisons(self):
        out = filter_reader_metadata(self.html, self.pages, {("page-a", 0), ("page-b", 0)})
        self.assertEqual(self.parse(out, "PAL"), [])
        self.assertEqual(self.parse(out, "HF"), [])
        self.assertNotIn("page-hidden", out)

    def test_two_complete_selected_witnesses_remain_without_hidden_metadata(self):
        out = filter_reader_metadata(self.html, self.pages, {("page-a", 0), ("page-a", 1)})
        pal = self.parse(out, "PAL")
        self.assertEqual([p["id"] for p in pal], ["comparison"])
        self.assertEqual(len(pal[0]["witnesses"]), 2)
        self.assertEqual(self.parse(out, "HF"), ["page-a"])
        self.assertNotIn("page-hidden", out)
        self.assertEqual(filter_reader_metadata(out, self.pages, {("page-a", 0), ("page-a", 1)}), out)

    def test_unrecognised_executable_literal_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Unsupported reader metadata"):
            filter_reader_metadata('const PAL = [getPrivatePages()];', self.pages, set())

    def test_source_template_is_filtered_for_single_real_piece(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "site/data/j.json").read_text())
        source = (root / "site/index.html").read_text()
        out = filter_reader_metadata(source, data["pages"], {("diary1", b) for b in range(6)})
        self.assertEqual(self.parse(out, "PAL"), [])
        self.assertEqual(self.parse(out, "HF"), [])
        self.assertNotIn('"diary53a"', out)


if __name__ == "__main__":
    unittest.main()
