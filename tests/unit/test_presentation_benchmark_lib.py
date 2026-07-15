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
            '<span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">'
            "100.40 MB</span></td>"
        )
        formatted = {
            "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg": "85.94 MB",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertIn("85.94 MB</span></td>", updated)
        self.assertNotIn("100.40 MB", updated)

    def test_apply_benchmark_bindings_preserves_sibling_spans(self) -> None:
        html = (
            '<div class="stat bad">'
            '<span class="num" data-benchmark="01-custom-jre-jlink/with-jlink-runtime/build_avg_ms">'
            "3,410 ms</span><span class=\"lbl\">With jlink</span></div>"
        )
        formatted = {
            "01-custom-jre-jlink/with-jlink-runtime/build_avg_ms": "610 ms",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertIn(
            'data-benchmark="01-custom-jre-jlink/with-jlink-runtime/build_avg_ms">610 ms</span>'
            '<span class="lbl">With jlink</span>',
            updated,
        )
        self.assertNotIn("3,410 ms", updated)

    def test_apply_benchmark_bindings_preserves_computed_suffix(self) -> None:
        html = (
            '<p class="muted">'
            '<span data-benchmark-computed="01-custom-jre-jlink/size_ratio">~1.5×</span> '
            "smaller image</p>"
        )
        computed = {"01-custom-jre-jlink/size_ratio": "~1.2×"}

        updated = apply_benchmark_bindings(html, {}, {}, computed)

        self.assertIn('<span data-benchmark-computed="01-custom-jre-jlink/size_ratio">~1.2×</span>', updated)
        self.assertIn("smaller image</p>", updated)

    def test_apply_table_cell_highlights_best_and_worst(self) -> None:
        html = (
            "<table><tbody>"
            "<tr>"
            "<td>with-jlink</td>"
            '<td class="good"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">X</span></td>'
            '<td class="good"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/build_avg_ms">X</span></td>'
            '<td><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">X</span></td>'
            "</tr>"
            "<tr>"
            "<td>temurin</td>"
            '<td><span data-benchmark="01-custom-jre-jlink/temurin-jre-image/image_mb_avg">X</span></td>'
            '<td class="risk"><span data-benchmark="01-custom-jre-jlink/temurin-jre-image/build_avg_ms">X</span></td>'
            '<td class="good"><span data-benchmark="01-custom-jre-jlink/temurin-jre-image/startup_avg_ms">X</span></td>'
            "</tr>"
            "</tbody></table>"
        )
        numeric = {
            "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg": 85.94,
            "01-custom-jre-jlink/temurin-jre-image/image_mb_avg": 130.28,
            "01-custom-jre-jlink/with-jlink-runtime/build_avg_ms": 610.0,
            "01-custom-jre-jlink/temurin-jre-image/build_avg_ms": 685.0,
            "01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms": 1367.0,
            "01-custom-jre-jlink/temurin-jre-image/startup_avg_ms": 1385.0,
        }

        updated = apply_benchmark_bindings(html, {}, numeric, {})

        self.assertIn('<td class="good"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">', updated)
        self.assertIn('<td class="risk"><span data-benchmark="01-custom-jre-jlink/temurin-jre-image/image_mb_avg">', updated)
        self.assertIn('<td class="good"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/build_avg_ms">', updated)
        self.assertIn('<td class="risk"><span data-benchmark="01-custom-jre-jlink/temurin-jre-image/build_avg_ms">', updated)
        self.assertIn(
            '<td class="good"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">', updated
        )
        self.assertIn(
            '<td class="warn"><span data-benchmark="01-custom-jre-jlink/temurin-jre-image/startup_avg_ms">', updated
        )

    def test_apply_table_cell_highlights_small_spread_uses_warn_not_risk(self) -> None:
        html = (
            "<table><tbody>"
            "<tr><td>with-jlink</td>"
            '<td class="risk"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">X</span></td></tr>'
            "<tr><td>without-jlink</td>"
            '<td class="good"><span data-benchmark="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">X</span></td></tr>'
            "</tbody></table>"
        )
        numeric = {
            "01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms": 1339.0,
            "01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms": 1265.0,
        }

        updated = apply_benchmark_bindings(html, {}, numeric, {})

        self.assertIn(
            '<td class="good"><span data-benchmark="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">', updated
        )
        self.assertIn(
            '<td class="warn"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">', updated
        )
        self.assertNotIn(
            'class="risk"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">', updated
        )

    def test_apply_table_cell_highlights_clears_stale_classes(self) -> None:
        html = (
            "<table><tbody>"
            '<tr><td class="good"><span data-benchmark="05-appcds/with-appcds/startup_avg_ms">X</span></td></tr>'
            '<tr><td><span data-benchmark="05-appcds/without-appcds/startup_avg_ms">X</span></td></tr>'
            "</tbody></table>"
        )
        numeric = {
            "05-appcds/with-appcds/startup_avg_ms": 1529.0,
            "05-appcds/without-appcds/startup_avg_ms": 1334.0,
        }

        updated = apply_benchmark_bindings(html, {}, numeric, {})

        self.assertIn('<td class="good"><span data-benchmark="05-appcds/without-appcds/startup_avg_ms">', updated)
        self.assertIn('<td class="risk"><span data-benchmark="05-appcds/with-appcds/startup_avg_ms">', updated)

    def test_apply_benchmark_bindings_skips_stamp_when_data_unchanged(self) -> None:
        html = (
            "<body>\n"
            "  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n"
            '<span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">'
            "85.94 MB</span></body>"
        )
        formatted = {
            "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg": "85.94 MB",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertEqual(updated, html)

    def test_apply_benchmark_bindings_updates_stamp_only_when_data_changes(self) -> None:
        html = (
            "<body>\n"
            "  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n"
            '<span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">'
            "100.40 MB</span></body>"
        )
        formatted = {
            "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg": "85.94 MB",
        }

        updated = apply_benchmark_bindings(html, formatted, {}, {})

        self.assertIn("85.94 MB</span>", updated)
        self.assertNotIn("2026-01-01T00:00:00Z", updated)
        self.assertRegex(updated, r"<!-- benchmark-updated: \d{4}-\d{2}-\d{2}T")

    def test_apply_benchmark_data_ignores_stamp(self) -> None:
        html = (
            "<body>\n"
            "  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n"
            '<span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">'
            "85.94 MB</span></body>"
        )
        formatted = {
            "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg": "85.94 MB",
        }

        updated = apply_benchmark_data(html, formatted, {}, {})

        self.assertEqual(updated, html)

    def test_touch_benchmark_stamp_replaces_existing_stamp(self) -> None:
        html = "<body>\n  <!-- benchmark-updated: 2026-01-01T00:00:00Z -->\n</body>"

        updated = touch_benchmark_stamp(html)

        self.assertNotIn("2026-01-01T00:00:00Z", updated)
        self.assertRegex(updated, r"<!-- benchmark-updated: \d{4}-\d{2}-\d{2}T")
