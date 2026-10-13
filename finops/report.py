"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly") -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        f"**Period:** {period}  ",
        f"**Baseline spend:** ${baseline_usd:,.0f}  ",
        f"**Optimized spend:** ${optimized_usd:,.0f}  ",
        f"**Projected savings:** ${savings:,.0f}  (**{pct:.0f}%**)",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability",
            "",
            f"- Energy per query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query: {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Cheapest+cleanest region: {sustainability.get('best_region', 'n/a')}",
        ]
        cache = sustainability.get("cache_economics")
        if cache:
            lines += [
                "",
                "### Extension: cache economics",
                "",
                f"- Average cache reads assumed: {cache.get('avg_cache_reads', 0):.1f}",
                f"- Break-even: {cache.get('break_even_reads', 0):.2f} reads",
                f"- Cache policy: {'enabled' if cache.get('cache_enabled') else 'disabled'} "
                f"({cache.get('cache_applied_rows', 0)}/{cache.get('cacheable_rows', 0)} eligible rows)",
            ]
        reasoning = sustainability.get("reasoning_budget")
        if reasoning:
            lines += [
                "",
                "### Extension: reasoning budget",
                "",
                f"- Reasoning traffic: {reasoning.get('reasoning_traffic_pct', 0):.1f}% of requests",
                f"- Reasoning share: {reasoning.get('reasoning_cost_pct', 0):.1f}% of optimized cost "
                f"and {reasoning.get('reasoning_wh_pct', 0):.1f}% of energy",
                f"- Estimated savings when capped at 10% traffic: "
                f"${reasoning.get('estimated_cap_savings_usd', 0):,.2f} and "
                f"{reasoning.get('estimated_cap_savings_wh', 0):,.2f} Wh",
            ]
        carbon = sustainability.get("carbon_schedule")
        if carbon:
            lines += [
                "",
                "### Extension: carbon-aware scheduling",
                "",
                f"- Interruptible jobs: {carbon.get('baseline_region', 'n/a')} -> "
                f"{carbon.get('target_region', 'n/a')}",
                f"- Estimated carbon saved: {carbon.get('carbon_saved_g', 0):,.2f} gCO2e "
                f"({carbon.get('carbon_reduction_pct', 0):.1f}%)",
                "- Trade-off: the cleanest region may increase latency or data-transfer cost.",
            ]
    lines += ["", "_Figures are June-2026 as-of snapshots; re-baseline before acting._"]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str) -> str:
    """Write a simple savings bar chart PNG. Returns the path. No-op if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(names, vals, color="#2e548a")
    ax.set_ylabel("Savings (USD / month)")
    ax.set_title("GPU cost savings by FinOps lever")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
