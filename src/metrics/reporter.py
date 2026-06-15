"""
Report generator for DesktopAgentBench.

Produces JSON, Markdown, and (future) HTML reports from benchmark metrics.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.metrics.calculator import BenchmarkMetrics, MetricResult


class Reporter:
    """Generates benchmark reports in multiple formats."""

    def __init__(self, results_dir: Path) -> None:
        self._results_dir = results_dir

    def generate_json(
        self, metrics: BenchmarkMetrics, run_id: str
    ) -> Path:
        """Generate a JSON report."""
        report_path = self._results_dir / run_id / "metrics.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        data = self._metrics_to_dict(metrics)
        data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        data["run_id"] = run_id

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return report_path

    def generate_markdown(
        self, metrics: BenchmarkMetrics, run_id: str
    ) -> Path:
        """Generate a Markdown report."""
        report_path = self._results_dir / run_id / "report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        lines.append(f"# DesktopAgentBench Report")
        lines.append(f"")
        lines.append(f"**Agent:** {metrics.agent_name}")
        lines.append(f"**Run ID:** {run_id}")
        lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Runs:** {metrics.total_runs}")
        lines.append(f"**Total Tasks:** {metrics.total_tasks}")
        lines.append(f"**Total Variants:** {metrics.total_variants}")
        lines.append("")

        # Summary table
        lines.append("## Metrics Summary")
        lines.append("")
        lines.append("| Metric | Abbrev. | Value | Description |")
        lines.append("|--------|---------|-------|-------------|")

        for metric in self._iter_metrics(metrics):
            direction = "↑" if metric.abbreviation not in ("UAR", "HAR", "LHDI") else "↓"
            lines.append(
                f"| {metric.name} | {metric.abbreviation} | "
                f"**{metric.value:.4f}** {direction} | {metric.description} |"
            )

        lines.append("")

        # Statistics (if available)
        stats_metrics = [m for m in self._iter_metrics(metrics) if m.stats]
        if stats_metrics:
            lines.append("## Statistical Analysis")
            lines.append("")
            lines.append("| Metric | Mean | Std | CI Lower | CI Upper | N |")
            lines.append("|--------|------|-----|----------|----------|---|")
            for m in stats_metrics:
                s = m.stats
                lines.append(
                    f"| {m.abbreviation} | {s.mean:.4f} | {s.std:.4f} | "
                    f"{s.ci_lower:.4f} | {s.ci_upper:.4f} | {s.n} |"
                )
            lines.append("")

        # Per-variant breakdown
        variant_metrics = [m for m in self._iter_metrics(metrics) if m.per_variant]
        if variant_metrics:
            lines.append("## Per-Variant Breakdown")
            lines.append("")
            for m in variant_metrics:
                lines.append(f"### {m.name} ({m.abbreviation})")
                lines.append("")
                lines.append("| Variant | Value |")
                lines.append("|---------|-------|")
                for v, val in sorted(m.per_variant.items()):
                    lines.append(f"| {v} | {val:.4f} |")
                lines.append("")

        # Per-task results
        if metrics.per_task_results:
            lines.append("## Per-Task Results")
            lines.append("")
            lines.append("| Task ID | TSR | Runs | Variants |")
            lines.append("|---------|-----|------|----------|")
            for task_id, data in sorted(metrics.per_task_results.items()):
                lines.append(
                    f"| {task_id} | {data['tsr']:.4f} | {data['total_runs']} | "
                    f"{', '.join(data['variants'])} |"
                )
            lines.append("")

        content = "\n".join(lines)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path

    def generate_comparison(
        self,
        all_metrics: list[BenchmarkMetrics],
        output_path: Path,
    ) -> Path:
        """Generate a comparison report across multiple agents."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        lines.append("# DesktopAgentBench — Agent Comparison")
        lines.append("")
        lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Agents compared:** {len(all_metrics)}")
        lines.append("")

        # Comparison table
        headers = ["Agent", "TSR ↑", "RS ↑", "RR ↑", "UAR ↓", "HAR ↓", "LHDI ↓", "ITS ↑"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")

        for m in all_metrics:
            lines.append(
                f"| {m.agent_name} | {m.tsr.value:.4f} | {m.rs.value:.4f} | "
                f"{m.rr.value:.4f} | {m.uar.value:.4f} | {m.har.value:.4f} | "
                f"{m.lhdi.value:.4f} | {m.its.value:.6f} |"
            )

        lines.append("")
        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    @staticmethod
    def _iter_metrics(metrics: BenchmarkMetrics) -> list[MetricResult]:
        """Iterate over all 7 metrics in order."""
        return [
            metrics.tsr, metrics.rs, metrics.rr,
            metrics.uar, metrics.har, metrics.lhdi, metrics.its,
        ]

    @staticmethod
    def _metrics_to_dict(metrics: BenchmarkMetrics) -> dict[str, Any]:
        """Convert BenchmarkMetrics to a serializable dict."""
        return asdict(metrics)
