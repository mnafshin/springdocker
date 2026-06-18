from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = str(ROOT / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from presentation_benchmark_lib import apply_benchmark_bindings, apply_benchmark_data, touch_benchmark_stamp


class PresentationBenchmarkLibTests(unittest.TestCase):
    def test_apply_benchmark_bindings_replaces_span_content(self) -> None:
        html = (
            '<td class="good">'
            '<span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg">'
            "100.40 MB</span></td>"
        )
        formatted = {
            "01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg": "164.56 MB",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertIn("164.56 MB</span></td>", updated)
        self.assertNotIn("100.40 MB", updated)

    def test_apply_benchmark_bindings_preserves_sibling_spans(self) -> None:
        html = (
            '<div class="stat bad">'
            '<span class="num" data-benchmark="02-buildkit-gradle-cache/without-buildkit-cache/build_avg_ms">'
            "3,410 ms</span><span class=\"lbl\">Without cache</span></div>"
        )
        formatted = {
            "02-buildkit-gradle-cache/without-buildkit-cache/build_avg_ms": "2,178 ms",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertIn(
            'data-benchmark="02-buildkit-gradle-cache/without-buildkit-cache/build_avg_ms">2,178 ms</span>'
            '<span class="lbl">Without cache</span>',
            updated,
        )
        self.assertNotIn("3,410 ms", updated)

    def test_apply_benchmark_bindings_preserves_computed_suffix(self) -> None:
        html = (
            '<p class="muted">'
            '<span data-benchmark-computed="02-buildkit-gradle-cache/build_speedup">~5.5×</span> '
            "faster rebuild</p>"
        )
        computed = {"02-buildkit-gradle-cache/build_speedup": "~3.4×"}

        updated = apply_benchmark_bindings(html, {}, {}, computed)

        self.assertIn('<span data-benchmark-computed="02-buildkit-gradle-cache/build_speedup">~3.4×</span>', updated)
        self.assertIn("faster rebuild</p>", updated)

    def test_apply_table_cell_highlights_best_and_worst(self) -> None:
        html = (
            "<table><tbody>"
            "<tr>"
            '<td>specialized</td>'
            '<td class="good"><span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg">X</span></td>'
            '<td class="good"><span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/build_avg_ms">X</span></td>'
            '<td><span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/startup_avg_ms">X</span></td>'
            "</tr>"
            "<tr>"
            '<td>simple</td>'
            '<td><span data-benchmark="01-multi-stage-build-structure/simple-two-stage/image_mb_avg">X</span></td>'
            '<td class="risk"><span data-benchmark="01-multi-stage-build-structure/simple-two-stage/build_avg_ms">X</span></td>'
            '<td class="good"><span data-benchmark="01-multi-stage-build-structure/simple-two-stage/startup_avg_ms">X</span></td>'
            "</tr>"
            "</tbody></table>"
        )
        numeric = {
            "01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg": 167.82,
            "01-multi-stage-build-structure/simple-two-stage/image_mb_avg": 130.32,
            "01-multi-stage-build-structure/specialized-multi-stage/build_avg_ms": 616.0,
            "01-multi-stage-build-structure/simple-two-stage/build_avg_ms": 637.0,
            "01-multi-stage-build-structure/specialized-multi-stage/startup_avg_ms": 1148.0,
            "01-multi-stage-build-structure/simple-two-stage/startup_avg_ms": 1367.0,
        }

        updated = apply_benchmark_bindings(html, {}, numeric, {})

        self.assertIn('<td class="good"><span data-benchmark="01-multi-stage-build-structure/simple-two-stage/image_mb_avg">', updated)
        self.assertIn('<td class="risk"><span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg">', updated)
        self.assertIn('<td class="good"><span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/build_avg_ms">', updated)
        self.assertIn('<td class="warn"><span data-benchmark="01-multi-stage-build-structure/simple-two-stage/build_avg_ms">', updated)
        self.assertIn('<td class="good"><span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/startup_avg_ms">', updated)
        self.assertIn('<td class="risk"><span data-benchmark="01-multi-stage-build-structure/simple-two-stage/startup_avg_ms">', updated)

    def test_apply_table_cell_highlights_small_spread_uses_warn_not_risk(self) -> None:
        html = (
            "<table><tbody>"
            '<tr><td>with-jlink</td>'
            '<td class="risk"><span data-benchmark="03-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">X</span></td></tr>'
            '<tr><td>without-jlink</td>'
            '<td class="good"><span data-benchmark="03-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">X</span></td></tr>'
            "</tbody></table>"
        )
        numeric = {
            "03-custom-jre-jlink/with-jlink-runtime/startup_avg_ms": 1339.0,
            "03-custom-jre-jlink/without-jlink-runtime/startup_avg_ms": 1265.0,
        }

        updated = apply_benchmark_bindings(html, {}, numeric, {})

        self.assertIn('<td class="good"><span data-benchmark="03-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">', updated)
        self.assertIn('<td class="warn"><span data-benchmark="03-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">', updated)
        self.assertNotIn('class="risk"><span data-benchmark="03-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">', updated)

    def test_apply_table_cell_highlights_clears_stale_classes(self) -> None:
        html = (
            "<table><tbody>"
            '<tr><td class="good"><span data-benchmark="08-appcds/with-appcds/startup_avg_ms">X</span></td></tr>'
            '<tr><td><span data-benchmark="08-appcds/without-appcds/startup_avg_ms">X</span></td></tr>'
            "</tbody></table>"
        )
        numeric = {
            "08-appcds/with-appcds/startup_avg_ms": 1529.0,
            "08-appcds/without-appcds/startup_avg_ms": 1334.0,
        }

        updated = apply_benchmark_bindings(html, {}, numeric, {})

        self.assertIn('<td class="good"><span data-benchmark="08-appcds/without-appcds/startup_avg_ms">', updated)
        self.assertIn('<td class="risk"><span data-benchmark="08-appcds/with-appcds/startup_avg_ms">', updated)

    def test_apply_benchmark_bindings_skips_stamp_when_data_unchanged(self) -> None:
        html = (
            "<body>\n"
            "  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n"
            '<span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg">'
            "164.56 MB</span></body>"
        )
        formatted = {
            "01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg": "164.56 MB",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertEqual(updated, html)

    def test_apply_benchmark_bindings_updates_stamp_only_when_data_changes(self) -> None:
        html = (
            "<body>\n"
            "  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n"
            '<span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg">'
            "100.40 MB</span></body>"
        )
        formatted = {
            "01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg": "164.56 MB",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertIn("164.56 MB</span>", updated)
        self.assertNotIn("2026-01-01T00:00:00Z", updated)
        self.assertRegex(updated, r"<!-- benchmark-updated: \d{4}-\d{2}-\d{2}T")

    def test_apply_benchmark_data_ignores_stamp(self) -> None:
        html = (
            "<body>\n"
            "  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n"
            '<span data-benchmark="01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg">'
            "164.56 MB</span></body>"
        )
        formatted = {
            "01-multi-stage-build-structure/specialized-multi-stage/image_mb_avg": "164.56 MB",
        }

        updated = apply_benchmark_data(html, formatted, {}, {})

        self.assertEqual(updated, html)

    def test_touch_benchmark_stamp_replaces_existing_stamp(self) -> None:
        html = "<body>\n  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n</body>"

        updated = touch_benchmark_stamp(html)

        self.assertNotIn("2026-01-01T00:00:00Z", updated)
        self.assertRegex(updated, r"<!-- benchmark-updated: \d{4}-\d{2}-\d{2}T")
