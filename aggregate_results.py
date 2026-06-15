"""
DesktopAgentBench — Task-Agnostic Results Aggregator

Scans the results/ directory, loads metrics for each agent,
groups tasks by category, computes statistics, tests hypotheses,
and generates a publication-ready report with markdown tables.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

def load_task_categories(tasks_dir: Path) -> dict[str, str]:
    """Dynamically load task_id -> category mapping from task definitions."""
    mapping = {}
    for path in tasks_dir.rglob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "task_id" in data and "category" in data:
                    mapping[data["task_id"]] = data["category"]
        except Exception as e:
            print(f"Warning: Failed to load task definition {path}: {e}")
    return mapping

def find_latest_sessions(results_dir: Path) -> dict[str, Path]:
    """Find the latest session directory for each agent."""
    agent_sessions: dict[str, tuple[float, Path]] = {}
    
    if not results_dir.exists():
        return {}
        
    for p in results_dir.iterdir():
        if p.is_dir() and p.name.startswith("session_"):
            metrics_path = p / "metrics.json"
            if metrics_path.exists():
                try:
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        agent = data.get("agent_name")
                        if agent:
                            mtime = metrics_path.stat().st_mtime
                            if agent not in agent_sessions or mtime > agent_sessions[agent][0]:
                                agent_sessions[agent] = (mtime, p)
                except Exception as e:
                    print(f"Warning: Failed to parse metrics in {p}: {e}")
                    
    return {agent: path for agent, (_, path) in agent_sessions.items()}

def main():
    results_dir = Path("results")
    tasks_dir = Path("tasks")
    
    # Load task categories
    task_categories = load_task_categories(tasks_dir)
    print(f"Loaded {len(task_categories)} task category mappings.")
    
    # Find latest sessions per agent
    sessions = find_latest_sessions(results_dir)
    print(f"Discovered latest sessions: {list(sessions.keys())}")
    
    if not sessions:
        print("Error: No agent session data found in results/.")
        sys.exit(1)
        
    # Load session metrics
    metrics: dict[str, dict] = {}
    for agent, path in sessions.items():
        with open(path / "metrics.json", "r", encoding="utf-8") as f:
            metrics[agent] = json.load(f)
            
    # List of metrics to compare
    metric_keys = ["tsr", "rs", "rr", "uar", "har", "lhdi", "its"]
    
    # 1. OVERALL METRICS TABLE
    overall_table = [
        "| Agent | TSR (Success Rate) ↑ | RS (Robustness) ↑ | RR (Recovery) ↑ | UAR (Unrecoverable) ↓ | HAR (Human Help) ↓ | LHDI (Latent Harm) ↓ | ITS (Throughput) ↑ |",
        "|-------|----------------------|-------------------|------------------|-----------------------|--------------------|----------------------|--------------------|"
    ]
    for agent in sorted(metrics.keys()):
        data = metrics[agent]
        row = [f"**{agent}**"]
        for key in metric_keys:
            val = data.get(key, {}).get("value", 0.0)
            if key == "its":
                row.append(f"{val:.6f}")
            else:
                row.append(f"{val:.4f}")
        overall_table.append("| " + " | ".join(row) + " |")
        
    # 2. PER-CHAOS BREAKDOWN TABLE
    # Determine all unique chaos variants across the agents
    all_variants = set()
    for agent, data in metrics.items():
        for key in metric_keys:
            per_var = data.get(key, {}).get("per_variant", {})
            all_variants.update(per_var.keys())
            
    sorted_variants = sorted(list(all_variants))
    # Standardize names for columns
    headers = ["Agent"] + [f"{v.replace('_', ' ').title()} TSR" for v in sorted_variants]
    chaos_table = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|"
    ]
    for agent in sorted(metrics.keys()):
        data = metrics[agent]
        per_var_tsr = data.get("tsr", {}).get("per_variant", {})
        row = [f"**{agent}**"]
        for v in sorted_variants:
            val = per_var_tsr.get(v, 0.0)
            row.append(f"{val:.4f}")
        chaos_table.append("| " + " | ".join(row) + " |")
        
    # 3. PER-CATEGORY BREAKDOWN TABLE
    # Determine all unique categories
    categories = sorted(list(set(task_categories.values())))
    cat_headers = ["Agent"] + [f"{cat.replace('_', ' ').title()} TSR" for cat in categories]
    cat_table = [
        "| " + " | ".join(cat_headers) + " |",
        "|" + "|".join(["---"] * len(cat_headers)) + "|"
    ]
    
    # We need to compute category TSR for each agent.
    # In each session, data["per_task_results"] maps task_id -> {"tsr": float}
    for agent in sorted(metrics.keys()):
        data = metrics[agent]
        per_task = data.get("per_task_results", {})
        
        # Group task TSRs by category
        cat_tsrs: dict[str, list[float]] = {cat: [] for cat in categories}
        for task_id, task_res in per_task.items():
            cat = task_categories.get(task_id)
            if cat in cat_tsrs:
                cat_tsrs[cat].append(task_res.get("tsr", 0.0))
                
        row = [f"**{agent}**"]
        for cat in categories:
            vals = cat_tsrs[cat]
            avg_tsr = sum(vals) / len(vals) if vals else 0.0
            row.append(f"{avg_tsr:.4f}")
        cat_table.append("| " + " | ".join(row) + " |")
        
    # 4. HYPOTHESIS TESTING
    hypothesis_results = []
    
    # H1: Combined chaos causes the largest degradation
    # Check if moderate/severe TSR is lower than all isolated TSRs for the rule agent
    rule_tsr = metrics.get("rule", {}).get("tsr", {})
    rule_per_var = rule_tsr.get("per_variant", {})
    if rule_per_var:
        clean_tsr = rule_per_var.get("clean", 0.0)
        isolated_tsrs = [rule_per_var[v] for v in rule_per_var if v not in ("clean", "moderate", "severe")]
        combined_tsr = rule_per_var.get("moderate", 0.0)
        
        is_h1_supported = False
        if isolated_tsrs:
            is_h1_supported = combined_tsr < min(isolated_tsrs) and combined_tsr < clean_tsr
            
        h1_status = "SUPPORTED" if is_h1_supported else "NOT SUPPORTED"
        hypothesis_results.append(
            f"**H1: Combined chaos causes the largest degradation** — **{h1_status}**\n"
            f"  - Clean Baseline TSR: {clean_tsr:.4f}\n"
            f"  - Isolated Chaos TSRs (Min/Max): {min(isolated_tsrs) if isolated_tsrs else 0.0:.4f}/{max(isolated_tsrs) if isolated_tsrs else 0.0:.4f}\n"
            f"  - Combined Chaos (Moderate) TSR: {combined_tsr:.4f}"
        )
    else:
        hypothesis_results.append("**H1: Combined chaos causes the largest degradation** — **INSUFFICIENT DATA**")
        
    # H2: Focus-aware agents recover better than naive agents
    # Compare Rule (focus-aware) RR vs Noop/Random (naive) RR
    rule_rr = metrics.get("rule", {}).get("rr", {}).get("value", 0.0)
    noop_rr = metrics.get("noop", {}).get("rr", {}).get("value", 0.0)
    random_rr = metrics.get("random", {}).get("rr", {}).get("value", 0.0)
    
    is_h2_supported = rule_rr > max(noop_rr, random_rr)
    h2_status = "SUPPORTED" if is_h2_supported else "NOT SUPPORTED"
    hypothesis_results.append(
        f"**H2: Focus-aware agents recover better than naive agents** — **{h2_status}**\n"
        f"  - Rule Agent (Focus-Aware) Recovery Rate: {rule_rr:.4f}\n"
        f"  - Noop Agent Recovery Rate: {noop_rr:.4f}\n"
        f"  - Random Agent Recovery Rate: {random_rr:.4f}"
    )
    
    # H3: Random agents create more latent harm than structured agents
    # Compare Random LHDI vs Noop & Rule LHDI
    rule_lhdi = metrics.get("rule", {}).get("lhdi", {}).get("value", 0.0)
    noop_lhdi = metrics.get("noop", {}).get("lhdi", {}).get("value", 0.0)
    random_lhdi = metrics.get("random", {}).get("lhdi", {}).get("value", 0.0)
    
    is_h3_supported = random_lhdi > max(noop_lhdi, rule_lhdi)
    h3_status = "SUPPORTED" if is_h3_supported else "NOT SUPPORTED"
    hypothesis_results.append(
        f"**H3: Random agents create more latent harm than structured agents** — **{h3_status}**\n"
        f"  - Random Agent Latent Harm Index: {random_lhdi:.4f}\n"
        f"  - Rule Agent Latent Harm Index: {rule_lhdi:.4f}\n"
        f"  - Noop Agent Latent Harm Index: {noop_lhdi:.4f}"
    )
    
    # Write publication-ready report
    report_lines = [
        "# DesktopAgentBench — Empirical Evaluation Report",
        "",
        "This report aggregates all baseline evaluations across the task corpus, groups tasks dynamically by category, and validates the benchmark's core hypotheses.",
        "",
        "## 1. Core Metrics Comparison Summary",
        "",
        "The following table compares the 7 core metrics computed across all runs in the matrix evaluation.",
        ""
    ] + overall_table + [
        "",
        "## 2. Disruption Profile Breakdown (TSR)",
        "",
        "The table below breaks down the Task Success Rate (TSR) across clean runs, isolated chaos modules, and combined chaos profiles.",
        ""
    ] + chaos_table + [
        "",
        "## 3. Dynamic Category Performance (TSR)",
        "",
        "The table below shows the average success rate (TSR) grouped dynamically by application category.",
        ""
    ] + cat_table + [
        "",
        "## 4. Hypothesis Testing & Validation",
        "",
        "We tested the three core hypotheses formulated for DesktopAgentBench reliability evaluation:",
        ""
    ] + [f"- {res}" for res in hypothesis_results] + [
        "",
        "## 5. Statistical Release Metadata",
        f"- **No-op Session Path:** {sessions.get('noop')}",
        f"- **Random Session Path:** {sessions.get('random')}",
        f"- **Rule Session Path:** {sessions.get('rule')}",
        "- **Status:** Frozen v1.0, task-agnostic aggregation complete."
    ]
    
    report_content = "\n".join(report_lines)
    report_path = results_dir / "evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Successfully generated dynamic evaluations report at {report_path.resolve()}")

if __name__ == "__main__":
    main()
