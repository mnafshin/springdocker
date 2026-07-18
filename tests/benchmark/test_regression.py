from __future__ import annotations

import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.analyze import VariantSummary
from springdocker.regression import detect_regressions, format_regression_json, format_regression_table, load_summaries


class RegressionTests(unittest.TestCase):
    def test_detect_regressions(self) -> None:
        baseline = [VariantSummary("s1", "v1", 1, 100.0, 200.0, 220.0, 100.0, 100.0)]
        current = [VariantSummary("s1", "v1", 1, 100.0, 250.0, 260.0, 120.0, 100.0)]
        violations = detect_regressions(baseline, current, threshold_pct=10.0)
        self.assertEqual({v.metric for v in violations}, {"startup_avg_ms", "startup_p95_ms", "image_mb_avg"})
        self.assertIn("startup_avg_ms", format_regression_table(violations))
        self.assertIn('"metric": "startup_avg_ms"', format_regression_json(violations))

    def test_missing_current_metric_is_regression(self) -> None:
        baseline = [VariantSummary("s1", "v1", 1, 100.0, 200.0, 220.0, 100.0, 100.0)]
        current = [VariantSummary("s1", "v1", 1, 100.0, None, None, None, 0.0)]
        violations = detect_regressions(baseline, current, threshold_pct=10.0)
        self.assertEqual(len(violations), 3)

    def test_missing_baseline_variant_is_ignored(self) -> None:
        baseline = [VariantSummary("s1", "v1", 1, 100.0, 200.0, 220.0, 100.0, 100.0)]
        current = [VariantSummary("s1", "v2", 1, 100.0, 200.0, 220.0, 100.0, 100.0)]
        violations = detect_regressions(baseline, current, threshold_pct=10.0)
        self.assertEqual(violations, [])

    def test_scenario_03_baseline_matches_committed_raw_csv(self) -> None:
        from springdocker.analyze import format_json, summarize_csv
        from tests.test_support import ROOT

        results = ROOT / "samples" / "java-spring-docker" / "benchmarks" / "03-base-image-choice" / "results"
        raw_csv = results / "raw.csv"
        baseline_path = results / "baseline.json"
        if not raw_csv.exists() or not baseline_path.exists():
            self.skipTest("sample checkout required: python scripts/checkout_sample.py")

        current = summarize_csv(raw_csv)
        baseline = load_summaries(baseline_path)
        self.assertEqual(format_json(current), format_json(baseline))


if __name__ == "__main__":
    unittest.main()
