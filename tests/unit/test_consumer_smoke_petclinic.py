from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_support import ROOT, add_src_to_path

add_src_to_path()

_SCRIPT = ROOT / "scripts" / "consumer_smoke_petclinic.py"
_spec = importlib.util.spec_from_file_location("consumer_smoke_petclinic", _SCRIPT)
assert _spec is not None and _spec.loader is not None
consumer_smoke = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = consumer_smoke
_spec.loader.exec_module(consumer_smoke)

ConsumerSmokeManifest = consumer_smoke.ConsumerSmokeManifest
ensure_sbom_placeholder = consumer_smoke.ensure_sbom_placeholder
load_manifest = consumer_smoke.load_manifest


class ConsumerSmokePetclinicTests(unittest.TestCase):
    def test_load_manifest(self) -> None:
        manifest = load_manifest(ROOT / "scripts" / "consumer_smoke_petclinic.manifest.json")
        self.assertEqual(manifest.build_tool, "maven")
        self.assertEqual(manifest.ref, "51045d1648dad955df586150c1a1a6e22ef400c2")
        self.assertEqual(manifest.configure_wizard_input, "4\n\n")

    def test_manifest_from_mapping_requires_core_keys(self) -> None:
        with self.assertRaises(KeyError):
            ConsumerSmokeManifest.from_mapping({"repository": "https://example.test/repo.git"})

    def test_ensure_sbom_placeholder_writes_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            destination = ensure_sbom_placeholder(root)
            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["spdxVersion"], "SPDX-2.3")
            self.assertTrue(destination.exists())

    def test_ensure_sbom_placeholder_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = ensure_sbom_placeholder(root)
            first.write_text('{"spdxVersion":"SPDX-2.3","name":"custom"}\n', encoding="utf-8")
            second = ensure_sbom_placeholder(root)
            self.assertEqual(second.read_text(encoding="utf-8"), first.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
