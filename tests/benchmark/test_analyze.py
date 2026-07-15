from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.analyze import format_json, format_table, summarize_csv


class AnalyzeTests(unittest.TestCase):
    def test_summarize_and_filter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text(
                "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes\n"
                "2026-01-01,s1,v1,1,100,1048576,200,ok,\n"
                "2026-01-01,s1,v1,2,200,1048576,300,ok,\n"
                "2026-01-01,s1,v2,1,-1,-1,-1,build_failed,x\n",
                encoding="utf-8",
            )
            all_rows = summarize_csv(csv_path)
            self.assertEqual(len(all_rows), 2)
            filtered = summarize_csv(csv_path, scenario="s1", variant="v1")
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0].runs, 2)
            self.assertAlmostEqual(filtered[0].build_avg_ms or 0.0, 150.0)

    def test_statistical_metrics_are_rounded_for_stable_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text(
                "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes\n"
                "2026-01-01,03-base-image-choice,debian-slim,1,1747,90110432,1591,ok,\n"
                "2026-01-01,03-base-image-choice,debian-slim,2,613,90110432,1327,ok,\n"
                "2026-01-01,03-base-image-choice,debian-slim,3,627,90110432,1320,ok,\n",
                encoding="utf-8",
            )
            summary = summarize_csv(csv_path)[0]
            self.assertEqual(summary.startup_stddev_ms, 154.480851)

    def test_missing_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text("scenario,variant\ns1,v1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                summarize_csv(csv_path)

    def test_output_formatters(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text(
                "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes\n"
                "2026-01-01,s1,v1,1,100,1048576,200,ok,\n",
                encoding="utf-8",
            )
            summaries = summarize_csv(csv_path)
            table = format_table(summaries)
            data = format_json(summaries)
            self.assertIn("| Scenario | Variant |", table)
            self.assertIn('"scenario": "s1"', data)

    def test_optional_metrics_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text(
                "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes,rss_bytes,cpu_pct,host,docker_version,run_profile\n"
                "2026-01-01,s1,v1,1,100,1048576,200,ok,,2097152,33.5,host1,24.0,quick\n",
                encoding="utf-8",
            )
            summaries = summarize_csv(csv_path)
            self.assertAlmostEqual(summaries[0].rss_mb_avg or 0.0, 2.0)
            self.assertAlmostEqual(summaries[0].cpu_pct_avg or 0.0, 33.5)
            self.assertEqual(summaries[0].host, "host1")
            self.assertIn('"rss_mb_avg": 2.0', format_json(summaries))

    def test_statistical_metrics_include_stddev_p99_and_ci95(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text(
                "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes\n"
                "2026-01-01,s1,v1,1,100,1048576,200,ok,\n"
                "2026-01-01,s1,v1,2,200,1048576,400,ok,\n"
                "2026-01-01,s1,v1,3,300,1048576,600,ok,\n",
                encoding="utf-8",
            )
            summaries = summarize_csv(csv_path)
            summary = summaries[0]
            self.assertIsNotNone(summary.build_stddev_ms)
            self.assertIsNotNone(summary.startup_p99_ms)
            self.assertIsNotNone(summary.startup_ci95_low_ms)
            payload = json.loads(format_json(summaries))
            self.assertIn("build_stddev_ms", payload[0])
            self.assertIn("startup_p99_ms", payload[0])
            table = format_table(summaries)
            self.assertIn("Build stddev (ms)", table)
            self.assertIn("Startup p99 (ms)", table)

    def test_profiling_metrics_are_reported_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "raw.csv"
            csv_path.write_text(
                "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes,gc_pause_ms,alloc_mb,"
                "startup_phase_boot_ms,startup_phase_context_ms,startup_phase_web_server_ms\n"
                "2026-01-01,s1,v1,1,100,1048576,200,ok,,5.0,12.5,30.0,40.0,50.0\n"
                "2026-01-01,s1,v1,2,120,1048576,220,ok,,7.0,14.5,35.0,45.0,55.0\n",
                encoding="utf-8",
            )
            summaries = summarize_csv(csv_path)
            summary = summaries[0]
            self.assertAlmostEqual(summary.gc_pause_ms_avg or 0.0, 6.0)
            self.assertAlmostEqual(summary.alloc_mb_avg or 0.0, 13.5)
            self.assertAlmostEqual(summary.startup_phase_boot_ms_avg or 0.0, 32.5)
            self.assertAlmostEqual(summary.startup_phase_total_ms_avg or 0.0, 127.5)
            payload = json.loads(format_json(summaries))
            self.assertIn("gc_pause_ms_avg", payload[0])
            self.assertIn("startup_phase_total_ms_avg", payload[0])
            table = format_table(summaries)
            self.assertIn("GC pause avg (ms)", table)
            self.assertIn("Startup phase total (ms)", table)


if __name__ == "__main__":
    unittest.main()
